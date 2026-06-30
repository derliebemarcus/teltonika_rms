def publishSarif(String sarifPath, String toolName = '', String commitSha = '') {
    def config = [file: sarifPath]
    if (toolName) {
        config.toolName = toolName
    }
    if (commitSha) {
        config.commitSha = commitSha
    }
    ciUploadSarif(config)
}

def publishCoveralls(String coveragePath) {
    ciUploadCoveralls(file: coveragePath)
}

return this
