import groovy.json.JsonOutput

void checkoutRepo() {
    checkout scmGit(
        branches: [[name: env.BRANCH_NAME ? "*/${env.BRANCH_NAME}" : '*/main']],
        extensions: [cloneOption(noTags: false, shallow: false, depth: 0)],
        userRemoteConfigs: [[
            url: 'https://github.com/derliebemarcus/teltonika_rms.git',
            credentialsId: 'github token'
        ]]
    )
}

void markReportFailure(String markerName, Closure body) {
    try {
        body()
    } catch (err) {
        sh "mkdir -p .ci-failures && touch .ci-failures/${markerName}.failed"
        throw err
    }
}

void unstashIfAvailable(String stashName) {
    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
        unstash stashName
    }
}

pipeline {
    agent none

    options {
        ansiColor('xterm')
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout()
    }

    environment {
        CI_BASE_IMAGE = 'registry.home.siczb.de/siczb/python-ci:latest'
        CI_IMAGE = "registry.home.siczb.de/siczb/teltonika-rms-ci:${env.BUILD_NUMBER}"
        CI_REGISTRY = 'https://registry.home.siczb.de'
        PYPI_URL = 'https://artifacts.home.siczb.de/repository/pypi-proxy/simple/'
        GITHUB_OWNER = 'derliebemarcus'
        GITHUB_REPO = 'teltonika_rms'
        SB_NAME = "build_sb_${env.BUILD_NUMBER}"
        CURRENT_STAGE = 'Initialize'
        CAPTURED_SHA = ''
        COMMIT_HASH = ''
        VERSION = ''
    }

    stages {
        stage('Initialize & Stash') {
            agent { label 'klymene' }
            steps {
                script {
                    env.CURRENT_STAGE = 'Initialize & Stash'
                    sh 'sudo rm -rf ./* ./.[!.]* || true'
                    checkoutRepo()
                    env.CAPTURED_SHA = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    env.COMMIT_HASH = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.VERSION = sh(
                        script: '''
                            python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("custom_components/teltonika_rms/manifest.json").read_text(encoding="utf-8"))["version"])
PY
                        ''',
                        returnStdout: true
                    ).trim()
                    sh '''
                        if grep -R "<<<<<<<\\|=======\\|>>>>>>>" requirements*.txt pyproject.toml custom_components tests tools 2>/dev/null; then
                            echo "Merge conflict markers detected."
                            exit 1
                        fi
                    '''
                    sh 'sudo chown -R $(id -u):$(id -g) . || true'
                    stash name: 'source', includes: '**/*', useDefaultExcludes: false
                }
            }
        }

        stage('Build CI Environment') {
            agent { label 'klymene' }
            steps {
                script {
                    env.CURRENT_STAGE = 'Build CI Environment'
                    try {
                        sh 'sudo rm -rf ./* ./.[!.]* || true'
                        unstash 'source'
                        sh """
                            cat <<'EOF' > Dockerfile.ci
FROM ${env.CI_BASE_IMAGE}
WORKDIR /build
USER root
RUN (apt-get update && apt-get install -y git curl ca-certificates) || (apk add --no-cache git curl ca-certificates) || true
COPY requirements-dev.txt ./
RUN python3 -m pip install --upgrade pip --index-url ${env.PYPI_URL}
RUN python3 -m pip install --index-url ${env.PYPI_URL} -r requirements-dev.txt
COPY pyproject.toml pytest.ini .coveragerc ./
COPY custom_components ./custom_components
COPY tests ./tests
COPY tools ./tools
EOF
                            podman build --pull=never -t ${env.CI_IMAGE} -f Dockerfile.ci .
                        """
                        withCredentials([usernamePassword(credentialsId: 'harbor-jenkins-user', usernameVariable: 'U', passwordVariable: 'P')]) {
                            sh """
                                podman login -u "\$U" -p "\$P" registry.home.siczb.de
                                podman push ${env.CI_IMAGE}
                            """
                        }
                    } finally {
                        sh 'sudo chown -R $(id -u):$(id -g) . || true'
                    }
                }
            }
        }

        stage('Parallel: Report-Producing QA') {
            failFast false
            parallel {
                stage('Pytest Coverage Report') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps {
                        script {
                            env.CURRENT_STAGE = 'Pytest Coverage Report'
                            sh 'sudo rm -rf ./* ./.[!.]* || true'
                            unstash 'source'
                            catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                                markReportFailure('pytest-coverage') {
                                    sh """
                                        mkdir -p ${env.SB_NAME}/sonar/tests
                                        python3 -m pytest tests/unit tests/ha \
                                          --junitxml=${env.SB_NAME}/sonar/tests/pytest.xml \
                                          --cov=. --cov-config=.coveragerc \
                                          --cov-report=xml:${env.SB_NAME}/sonar/tests/coverage.xml \
                                          --cov-report=term-missing
                                        python3 tools/check_coverage_threshold.py ${env.SB_NAME}/sonar/tests/coverage.xml 97.1
                                    """
                                }
                            }
                        }
                    }
                    post { always { stash name: 'report-pytest-coverage', includes: "${env.SB_NAME}/sonar/tests/**", allowEmpty: true; stash name: 'qa-failure-marker-pytest-coverage', includes: '.ci-failures/pytest-coverage.failed', allowEmpty: true; junit allowEmptyResults: true, testResults: "${env.SB_NAME}/sonar/tests/pytest.xml"; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/tests/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Ruff Lint Report') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps { script { env.CURRENT_STAGE = 'Ruff Lint Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('ruff-lint') { sh "mkdir -p ${env.SB_NAME}/sonar/ruff && python3 -m ruff check . --output-format=json --output-file=${env.SB_NAME}/sonar/ruff/ruff-report.json" } } } }
                    post { always { stash name: 'report-ruff-lint', includes: "${env.SB_NAME}/sonar/ruff/**", allowEmpty: true; stash name: 'qa-failure-marker-ruff-lint', includes: '.ci-failures/ruff-lint.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/ruff/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Ruff Format Report') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps { script { env.CURRENT_STAGE = 'Ruff Format Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('ruff-format') { sh "mkdir -p ${env.SB_NAME}/sonar/ruff-format && python3 -m ruff format --check . > ${env.SB_NAME}/sonar/ruff-format/ruff-format.txt 2>&1" } } } }
                    post { always { stash name: 'report-ruff-format', includes: "${env.SB_NAME}/sonar/ruff-format/**", allowEmpty: true; stash name: 'qa-failure-marker-ruff-format', includes: '.ci-failures/ruff-format.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/ruff-format/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Mypy Report') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps { script { env.CURRENT_STAGE = 'Mypy Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('mypy') { sh "mkdir -p ${env.SB_NAME}/sonar/mypy && python3 -m mypy . --show-column-numbers > ${env.SB_NAME}/sonar/mypy/mypy-report.txt" } } } }
                    post { always { stash name: 'report-mypy', includes: "${env.SB_NAME}/sonar/mypy/**", allowEmpty: true; stash name: 'qa-failure-marker-mypy', includes: '.ci-failures/mypy.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/mypy/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Translation Validation Report') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps { script { env.CURRENT_STAGE = 'Translation Validation Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('translations') { sh "mkdir -p ${env.SB_NAME}/sonar/translations && python3 tools/check_translations.py > ${env.SB_NAME}/sonar/translations/translations.txt 2>&1" } } } }
                    post { always { stash name: 'report-translations', includes: "${env.SB_NAME}/sonar/translations/**", allowEmpty: true; stash name: 'qa-failure-marker-translations', includes: '.ci-failures/translations.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/translations/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Pip Audit Report') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps { script { env.CURRENT_STAGE = 'Pip Audit Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('pip-audit') { sh """
                        mkdir -p ${env.SB_NAME}/sonar/pip-audit
                        python3 -m pip_audit -r requirements-dev.txt --format json --output ${env.SB_NAME}/sonar/pip-audit/pip-audit-report.json \
                          --ignore-vuln CVE-2025-67221 --ignore-vuln CVE-2026-32597 --ignore-vuln CVE-2026-27448 --ignore-vuln CVE-2026-27459 \
                          --ignore-vuln CVE-2026-4539 --ignore-vuln CVE-2026-25645 --ignore-vuln CVE-2026-34073 --ignore-vuln CVE-2026-39892 \
                          --ignore-vuln GHSA-pjjw-68hj-v9mw --ignore-vuln CVE-2026-34513 --ignore-vuln CVE-2026-34525 --ignore-vuln CVE-2026-34519 \
                          --ignore-vuln CVE-2026-34520 --ignore-vuln CVE-2026-34517
                    """ } } } }
                    post { always { stash name: 'report-pip-audit', includes: "${env.SB_NAME}/sonar/pip-audit/**", allowEmpty: true; stash name: 'qa-failure-marker-pip-audit', includes: '.ci-failures/pip-audit.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/pip-audit/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Gitleaks Report') {
                    agent { label 'klymene' }
                    steps { script { env.CURRENT_STAGE = 'Gitleaks Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; checkoutRepo(); catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('gitleaks') { sh """
                        mkdir -p ${env.SB_NAME}/sonar/gitleaks
                        podman run --rm -v "\$PWD:/repo:z" -w /repo docker.io/zricethezav/gitleaks:latest detect --source=/repo --redact --verbose --report-format=json --report-path=${env.SB_NAME}/sonar/gitleaks/gitleaks-report.json
                    """ } } } }
                    post { always { stash name: 'report-gitleaks', includes: "${env.SB_NAME}/sonar/gitleaks/**", allowEmpty: true; stash name: 'qa-failure-marker-gitleaks', includes: '.ci-failures/gitleaks.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/gitleaks/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Trivy FS Report') {
                    agent { label 'klymene' }
                    steps { script { env.CURRENT_STAGE = 'Trivy FS Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('trivy') { sh """
                        mkdir -p ${env.SB_NAME}/sonar/trivy
                        podman run --rm -v "\$PWD:/app:z" -w /app docker.io/aquasec/trivy:latest fs . --severity HIGH,CRITICAL --format json --output ${env.SB_NAME}/sonar/trivy/trivy-report.json --no-progress
                    """ } } } }
                    post { always { stash name: 'report-trivy', includes: "${env.SB_NAME}/sonar/trivy/**", allowEmpty: true; stash name: 'qa-failure-marker-trivy', includes: '.ci-failures/trivy.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/trivy/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('CodeQL Report') {
                    agent { label 'klymene' }
                    steps { script { env.CURRENT_STAGE = 'CodeQL Report'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') { markReportFailure('codeql') { def codeqlHome = tool name: 'codeql'; withEnv(["CODEQL_HOME=${codeqlHome}", "PATH=${codeqlHome}:${codeqlHome}/codeql:${env.PATH}"]) { sh """
                        set -eu
                        mkdir -p ${env.SB_NAME}/codeql ${env.SB_NAME}/sonar/codeql
                        CODEQL_BIN="\$(command -v codeql || true)"
                        if [ -z "\$CODEQL_BIN" ]; then CODEQL_BIN="\$(find "\$CODEQL_HOME" -type f -name codeql | head -1)"; fi
                        "\$CODEQL_BIN" version
                        "\$CODEQL_BIN" database create ${env.SB_NAME}/codeql/db-python --language=python --source-root=. --overwrite
                        "\$CODEQL_BIN" database analyze ${env.SB_NAME}/codeql/db-python codeql/python-queries:codeql-suites/python-security-and-quality.qls --format=sarif-latest --sarif-category=python --output=${env.SB_NAME}/sonar/codeql/codeql-python.sarif
                    """ } } } } }
                    post { always { stash name: 'report-codeql', includes: "${env.SB_NAME}/sonar/codeql/**", allowEmpty: true; stash name: 'qa-failure-marker-codeql', includes: '.ci-failures/codeql.failed', allowEmpty: true; archiveArtifacts artifacts: "${env.SB_NAME}/sonar/codeql/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }
            }
        }

        stage('Parallel: Blocking Gates') {
            failFast false
            parallel {
                stage('SonarQube Scan') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps { script {
                        env.CURRENT_STAGE = 'SonarQube Scan'
                        sh 'sudo rm -rf ./* ./.[!.]* || true'
                        unstash 'source'
                        ['report-pytest-coverage','report-ruff-lint','report-ruff-format','report-mypy','report-translations','report-pip-audit','report-gitleaks','report-trivy','report-codeql'].each { unstashIfAvailable(it) }
                        sh "mkdir -p ${env.SB_NAME}/sonar && find ${env.SB_NAME}/sonar -type f | sort || true"
                        withSonarQubeEnv('SonarQube') {
                            withCredentials([string(credentialsId: 'Sonarqube', variable: 'SONAR_TOKEN')]) {
                                sh """
                                    set -eu
                                    SONAR_BIN="\$(command -v sonar-scanner || true)"
                                    if [ -z "\$SONAR_BIN" ] && command -v pysonar >/dev/null 2>&1; then SONAR_BIN="\$(command -v pysonar)"; fi
                                    if [ -z "\$SONAR_BIN" ]; then echo "Neither sonar-scanner nor pysonar is available in the CI image."; exit 1; fi
                                    SONAR_ARGS="-Dsonar.host.url=https://sonarqube.home.siczb.de -Dsonar.token=\${SONAR_TOKEN} -Dsonar.projectKey=teltonika_rms -Dsonar.projectName=teltonika_rms -Dsonar.projectVersion=${env.VERSION}-${env.COMMIT_HASH} -Dsonar.python.version=3.14 -Dsonar.sources=custom_components/teltonika_rms -Dsonar.tests=tests"
                                    if [ -f "${env.SB_NAME}/sonar/tests/coverage.xml" ]; then SONAR_ARGS="\$SONAR_ARGS -Dsonar.python.coverage.reportPaths=${env.SB_NAME}/sonar/tests/coverage.xml"; fi
                                    if [ -f "${env.SB_NAME}/sonar/tests/pytest.xml" ]; then SONAR_ARGS="\$SONAR_ARGS -Dsonar.python.xunit.reportPath=${env.SB_NAME}/sonar/tests/pytest.xml"; fi
                                    "\$SONAR_BIN" \$SONAR_ARGS
                                """
                            }
                        }
                    } }
                    post { always { sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Mutation Testing') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    options { timeout(time: 45, unit: 'MINUTES') }
                    steps { script { env.CURRENT_STAGE = 'Mutation Testing'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; sh """
                        mkdir -p ${env.SB_NAME}/mutation
                        python3 -m pytest --cov=custom_components/teltonika_rms --cov-context=test --cov-config=.coveragerc tests/
                        python3 -m mutmut run
                        python3 -m mutmut results > ${env.SB_NAME}/mutation/mutation-results.txt || true
                    """ } }
                    post { always { archiveArtifacts artifacts: "${env.SB_NAME}/mutation/**,mutants/.mutmut-cache/**", allowEmptyArchive: true; sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Repository Rules') {
                    agent { docker { image "${env.CI_IMAGE}"; registryUrl "${env.CI_REGISTRY}"; registryCredentialsId 'harbor-jenkins-user'; label 'klymene'; args '-u root:root' } }
                    steps { script { env.CURRENT_STAGE = 'Repository Rules'; sh 'sudo rm -rf ./* ./.[!.]* || true'; checkoutRepo(); sh '''
                        set -eu
                        if [ -n "${CHANGE_TARGET:-}" ]; then
                            git fetch origin "${CHANGE_TARGET}:refs/remotes/origin/${CHANGE_TARGET}" || true
                            RANGE="$(git merge-base HEAD "origin/${CHANGE_TARGET}" || git rev-parse HEAD^)..HEAD"
                        elif [ -n "${GIT_PREVIOUS_SUCCESSFUL_COMMIT:-}" ] && git rev-parse --verify "${GIT_PREVIOUS_SUCCESSFUL_COMMIT}^{commit}" >/dev/null 2>&1; then
                            RANGE="${GIT_PREVIOUS_SUCCESSFUL_COMMIT}..HEAD"
                        else
                            RANGE="HEAD^..HEAD"
                        fi
                        echo "Commit range: ${RANGE}"
                        python3 tools/check_commit_messages.py "${RANGE}"
                        python3 tools/check_release_notes.py custom_components/teltonika_rms/manifest.json CHANGELOG.md
                    ''' } }
                    post { always { sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Hassfest') {
                    agent { label 'klymene' }
                    steps { script { env.CURRENT_STAGE = 'Hassfest'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; sh 'podman run --rm -v "$PWD:/github/workspace:z" ghcr.io/home-assistant/actions/hassfest:latest' } }
                    post { always { sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('OSV Scanner') {
                    agent { label 'klymene' }
                    steps { script { env.CURRENT_STAGE = 'OSV Scanner'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; sh 'podman run --rm -v "$PWD:/src:z" ghcr.io/google/osv-scanner:latest scan source -r --no-resolve /src' } }
                    post { always { sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }

                stage('Actionlint') {
                    agent { label 'klymene' }
                    steps { script { env.CURRENT_STAGE = 'Actionlint'; sh 'sudo rm -rf ./* ./.[!.]* || true'; unstash 'source'; sh 'podman run --rm -v "$PWD:/repo:z" -w /repo docker.io/rhysd/actionlint:latest' } }
                    post { always { sh 'sudo chown -R $(id -u):$(id -g) . || true' } }
                }
            }
        }

        stage('Finalize Quality Gate Result') {
            agent { label 'klymene' }
            steps { script {
                env.CURRENT_STAGE = 'Finalize Quality Gate Result'
                sh 'sudo rm -rf ./* ./.[!.]* || true'
                ['qa-failure-marker-pytest-coverage','qa-failure-marker-ruff-lint','qa-failure-marker-ruff-format','qa-failure-marker-mypy','qa-failure-marker-translations','qa-failure-marker-pip-audit','qa-failure-marker-gitleaks','qa-failure-marker-trivy','qa-failure-marker-codeql'].each { unstashIfAvailable(it) }
                sh 'find .ci-failures -type f -print 2>/dev/null || true'
                def failedReports = sh(script: 'test -d .ci-failures && find .ci-failures -type f | wc -l || echo 0', returnStdout: true).trim()
                if (failedReports != '0') {
                    error('One or more report-producing QA stages failed. See .ci-failures markers and archived reports.')
                }
            } }
        }
    }

    post {
        always {
            script {
                def buildResult = currentBuild.currentResult ?: 'SUCCESS'
                def githubStatus = buildResult == 'ABORTED' ? 'FAILURE' : buildResult
                def checksConclusion = buildResult == 'SUCCESS' ? 'SUCCESS' : (buildResult == 'UNSTABLE' ? 'NEUTRAL' : 'FAILURE')
                def failedStage = buildResult == 'SUCCESS' ? '' : (env.CURRENT_STAGE ?: 'unknown')
                githubNotify(credentialsId: 'github token', status: githubStatus, context: 'Continuous Integration / Jenkins', description: failedStage ? "Build ${buildResult} in stage: ${failedStage}" : "Build ${buildResult}", account: env.GITHUB_OWNER, repo: env.GITHUB_REPO, sha: env.CAPTURED_SHA ?: 'main')
                publishChecks(name: 'Jenkins Build', title: 'Teltonika RMS Quality Gates', summary: failedStage ? "Status: ${buildResult}\nStage: ${failedStage}" : "Status: ${buildResult}", conclusion: checksConclusion, status: 'COMPLETED')
                node('klymene') {
                    sh "podman rmi ${env.CI_IMAGE} || true"
                    withCredentials([usernamePassword(credentialsId: 'harbor-jenkins-user', usernameVariable: 'U', passwordVariable: 'P')]) {
                        sh "curl -s -u \"\$U:\$P\" -X DELETE \"https://registry.home.siczb.de/api/v2.0/projects/siczb/repositories/teltonika-rms-ci/artifacts/${env.BUILD_NUMBER}\" || true"
                    }
                    sh 'sudo chown -R $(id -u):$(id -g) ${WORKSPACE} 2>/dev/null || true'
                }
            }
        }
    }
}
