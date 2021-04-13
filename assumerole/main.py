"""
Switch between AWS profiles. You will be prompted for MFA code if needed.

Assumptions:
* Profiles are configured in ~/.aws/config
* Credentials are in ~/.aws/credentials

Usage:
    assume -h | --help
    assume PROFILE [options]

Options:
    --refresh  Request new auth token even if the current one is not expired.
"""
from assumerole.utility import assume_role_wrapper
from docopt import docopt

if __name__ == "__main__":
    args = docopt(__doc__)
    assume_role_wrapper(args["PROFILE"], args["--refresh"])
