# assumerole
`assumerole` is a utility for switching between multiple AWS profiles.

Similar projects:
* [assume-role](https://github.com/remind101/assume-role)

## Install
* Run `poetry install` inside repo directory
* Ensure you have a valid [AWS CLI configuration][1].

[1]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html

## Usage
* Print environment variables (doesn't actually set anything): `assume PROFILE`
* Activate variables (until shell exits): `$(assume PROFILE)`
* See detailed syntax: `assume --help`
