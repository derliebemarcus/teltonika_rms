import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";

const fail = (message) => { throw new Error(message); };
const run = (command, args, capture = false, input) => {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    stdio: capture ? "pipe" : "inherit",
    input,
    env: process.env,
  });
  if (result.status !== 0) fail(`${command} ${args.join(" ")} failed:\n${result.stderr || result.stdout}`);
  return capture ? result.stdout.trim() : "";
};
const gh = (endpoint, method = "GET", payload, allow404 = false) => {
  const args = ["api", ...(method === "GET" ? [] : ["--method", method]), endpoint];
  if (payload !== undefined) args.push("--input", "-");
  const result = spawnSync("gh", args, {
    encoding: "utf8",
    input: payload === undefined ? undefined : JSON.stringify(payload),
    env: process.env,
  });
  if (allow404 && result.status !== 0 && /404|Not Found/i.test(result.stderr)) return null;
  if (result.status !== 0) fail(`gh ${args.join(" ")} failed:\n${result.stderr}`);
  return result.stdout.trim() ? JSON.parse(result.stdout) : null;
};
const index = (items, key) => {
  const result = new Map();
  for (const item of items) if (!result.has(item[key])) result.set(item[key], item);
  return result;
};

async function waitForChecks(repository, sha, config) {
  const requiredWorkflows = config.required_workflows ?? [];
  const requiredStatuses = config.required_statuses ?? [];
  const deadline = Date.now() + (config.timeout_seconds ?? 1200) * 1000;
  while (true) {
    const workflows = index(
      gh(`repos/${repository}/actions/runs?event=push&head_sha=${sha}&per_page=100`).workflow_runs ?? [],
      "name",
    );
    const statuses = index(gh(`repos/${repository}/commits/${sha}/status`).statuses ?? [], "context");
    const missing = [
      ...requiredWorkflows.filter((name) => !workflows.has(name)),
      ...requiredStatuses.filter((name) => !statuses.has(name)),
    ];
    const pending = [
      ...requiredWorkflows.filter((name) => workflows.get(name)?.status !== "completed"),
      ...requiredStatuses.filter((name) => statuses.get(name)?.state === "pending"),
    ];
    const failed = [
      ...requiredWorkflows.filter((name) => {
        const run = workflows.get(name);
        return run?.status === "completed" && run.conclusion !== "success";
      }),
      ...requiredStatuses.filter((name) => ["error", "failure"].includes(statuses.get(name)?.state)),
    ];
    console.log(`checks: missing=[${missing}] pending=[${pending}] failed=[${failed}]`);
    if (failed.length) fail(`Required checks failed: ${failed.join(", ")}`);
    if (!missing.length && !pending.length) return;
    if (Date.now() >= deadline) fail(`Timed out waiting for checks on ${sha}.`);
    await new Promise((resolve) => setTimeout(resolve, 15_000));
  }
}

async function main() {
  const tag = process.argv[2];
  if (!/^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(tag ?? "")) fail(`Invalid release tag: ${tag ?? "<empty>"}`);
  const repository = process.env.GITHUB_REPOSITORY;
  if (!repository || !process.env.GH_TOKEN) fail("GITHUB_REPOSITORY and GH_TOKEN are required.");

  const config = JSON.parse(readFileSync(".github/release-publish.json", "utf8"));
  const version = tag.slice(1);
  const sha = run("git", ["rev-list", "-n", "1", tag], true);
  if (!sha) fail(`Unable to resolve ${tag}.`);
  await waitForChecks(repository, sha, config);

  const versionDocument = JSON.parse(readFileSync(config.version.path, "utf8"));
  const actualVersion = (config.version.property ?? "version")
    .split(".")
    .reduce((value, key) => value?.[key], versionDocument);
  if (String(actualVersion ?? "") !== version) fail(`${tag} does not match ${config.version.path}: ${actualVersion ?? "<empty>"}`);

  if (config.npm?.enabled) {
    run("npm", ["ci", "--ignore-scripts"]);
    run("npm", ["test"]);
    run("npm", ["run", "build"]);
    for (const path of config.npm.verify_clean ?? []) run("git", ["diff", "--exit-code", "--", path]);
  }
  if (config.asset && !existsSync(config.asset)) fail(`Missing release asset: ${config.asset}`);

  const changelog = readFileSync(config.changelog_path ?? "CHANGELOG.md", "utf8");
  const escaped = version.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const heading = new RegExp(`^## \\[${escaped}\\].*$`, "m").exec(changelog);
  if (!heading) fail(`No changelog section for ${version}.`);
  const bodyStart = heading.index + heading[0].length;
  const next = /^## \[/gm;
  next.lastIndex = bodyStart;
  const body = changelog.slice(bodyStart, next.exec(changelog)?.index ?? changelog.length).trim();
  if (!body) fail(`Empty changelog section for ${version}.`);

  const prerelease = version.includes("-");
  const payload = { tag_name: tag, name: `Release ${tag}`, body, prerelease, make_latest: prerelease ? "false" : "true" };
  const release = gh(`repos/${repository}/releases/tags/${tag}`, "GET", undefined, true);
  gh(release ? `repos/${repository}/releases/${release.id}` : `repos/${repository}/releases`, release ? "PATCH" : "POST", payload);
  if (config.asset) run("gh", ["release", "upload", tag, config.asset, "--clobber"]);

  const floating = prerelease ? config.floating_tags?.prerelease : config.floating_tags?.stable;
  if (floating) {
    run("git", ["config", "user.name", "github-actions[bot]"]);
    run("git", ["config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"]);
    run("git", ["tag", "-f", floating, sha]);
    run("git", ["push", "origin", "-f", `refs/tags/${floating}`]);
  }
}

main().catch((error) => {
  console.error(error.stack ?? error);
  process.exitCode = 1;
});
