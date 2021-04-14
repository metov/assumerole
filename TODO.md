# Future goals
Some features that may or may not be implemented in the future (PRs welcome!):

* Cache tokens
    * Save all auth responses to a cache
    * Don't request new token if old one isn't expired 
    * Support `--refresh` to force new token
* Save to file with `--persist`
    * Write credentials to `default` profile
    * Allows persisting role between shell sessions
    * If another `default` already exists, can prompt user about whether to override or abort
* Non-interactive support
    * `--mfa` argument so it doesn't ask the MFA code
    * Other optional args to support fully non-interactive usage (for scripts)
* Interactive mode when no args given
    * Use questionary to let user pick from available profiles
* Log expiration date
* Publish to Pypi