"""
Compose environment variables for switching between AWS profiles. If MFA is
required, you will be prompted for it. You must have a valid AWS config with
the profiles you want to use. See:
    https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html

Usage:
    assume -h | --help
    assume PROFILE [options]
"""
import json
import logging
from datetime import datetime

import boto3
import coloredlogs
import humanize as humanize
import pytz as pytz
import questionary
from botocore.session import Session
from docopt import docopt

# Set up logging TODO: This log config should only be active when using the CLI
log = logging.getLogger(__name__)
fmt = "%(programname)s:%(lineno)d %(levelname)s %(message)s"
coloredlogs.install(fmt=fmt, level="DEBUG", logger=log)


def cli():
    args = docopt(__doc__)

    # Compose command and print
    auth = assume_profile_role(args["PROFILE"])
    envars = compose_envars(auth)

    print(envars)


def assume_profile_role(role_profile):
    """Assume role described by role_profile and return the auth response."""

    # Get local profile config
    config = Session(profile=role_profile).get_scoped_config()

    # Construct assume role request
    assert "role_arn" in config, f"{role_profile} does not have role_arn."
    rq = {
        "RoleArn": config["role_arn"],
        "RoleSessionName": "test",
    }

    # Add MFA token if needed
    if "mfa_serial" in config:
        rq["SerialNumber"] = config["mfa_serial"]
        rq["TokenCode"] = questionary.text("Enter MFA code:").ask()

    # If source_profile is given, we should use it instead of the default profile
    source_profile = config.get("source_profile")
    log.info(f"Using source profile: {source_profile}")

    # Get auth token
    session = boto3.Session(profile_name=source_profile)
    sts = session.client("sts")
    response = sts.assume_role(**rq)

    # Log auth token
    resp_str = json.dumps(response, indent=4, default=lambda o: str(o))
    log.debug(f"Auth token:\n{resp_str}")

    # Log expiration date
    exp = response["Credentials"]["Expiration"]
    remaining = humanize.naturaldelta(exp - datetime.now(pytz.utc))
    log.info(f"The token will expire after {remaining} on {exp}")

    return response


def compose_envars(auth_response):
    """Given response from assume-role, compose shell commands for setting auth
    environment variables."""
    creds = auth_response["Credentials"]
    envars = {
        "AWS_ACCESS_KEY_ID": creds["AccessKeyId"],
        "AWS_SECRET_ACCESS_KEY": creds["SecretAccessKey"],
        "AWS_SESSION_TOKEN": creds["SessionToken"],
    }

    return "\n".join(f"export {k}={v}" for k, v in envars.items())
