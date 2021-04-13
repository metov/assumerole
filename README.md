# assumerole
`assumerole` is a utility for switching between multiple AWS profiles. Under the hood, it wraps [`aws sts assume-role`](https://docs.aws.amazon.com/cli/latest/reference/sts/assume-role.html).

Similar projects:
* [assume-role](https://github.com/remind101/assume-role)

## Install
1. Install AWS SDK
2. Put AWS credentials in `~/.aws/credentials`
3. Put AWS profiles in `~/.aws/config`
4. ```pip install --index-url https://test.pypi.org/simple/  assumerole```

## Update
```pip install -U --index-url https://test.pypi.org/simple/  assumerole```

## Usage
```
assume --profile <aws-profile-name>
```
You will be prompted for your MFA code if needed.

### Token caching
Auth tokens are cached in `~/.aws/cached_tokens`. New tokens will not be requested from AWS if these have not expired. To force a new request, use `--refresh`.

A history of all successful commands is in `~/.aws/assume_role_history`.

### TODO:
- Perform comprehensive coverage testing. Once package is tested fully, it will be made available in pypi.org
- In the meantime, do test it out and feel free to submit PRs
