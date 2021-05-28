"""
Compose environment variables for switching between AWS profiles. If MFA is
required, you will be prompted for it. You must have a valid AWS config with
the profiles you want to use. See:
    https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html

Usage:
    assume -h | --help
    assume PROFILE [options]

Options:
    --session=NAME   Use custom session name (defaults to use@host).
    --duration=SECS
        Specify session duration. Use "aws iam get-role" to check max duration
        confirmed for that session - if you ask for more than that, the request
        will be denied by AWS.
"""
import json
import logging
import os
import pwd
import socket
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path

import boto3
import coloredlogs
import humanize as humanize
import pytz as pytz
import questionary
from botocore.session import Session
from docopt import docopt

# Set up logging
# TODO: This log config should only be active when using the CLI
log = logging.getLogger(__name__)
fmt = "%(programname)s:%(lineno)d %(levelname)s %(message)s"
coloredlogs.install(fmt=fmt, level="DEBUG", logger=log)

CACHE_FILE = Path("~").expanduser() / ".local/share/assumerole/cache.json"


def cli():
    args = docopt(__doc__)

    # Compose command and print
    duration = int(args["--duration"] or 0)
    auth = assume_profile_role(args["PROFILE"], args["--session"], duration)
    envars = compose_envars(auth)

    print(envars)


def get_default_session_name():
    """The session name is mostly for logging[1]. By default, we use user@host,
    unless the user requests something else.

    [1] https://docs.aws.amazon.com/sdkref/latest/guide/setting-global-role_session_name.html
    """

    user = pwd.getpwuid(os.getuid()).pw_name
    host, _, _ = socket.gethostname().partition(".")
    return f"{user}@{host}"


def get_max_duration(role_arn):
    """
    Best guess for max duration allowed by role.

    It's possible to find out the actual allowed max duration using
    "aws iam get-role" [1]. However, unfortunately running get-role itself
    usually requires being authenticated, so we have to guess.

    Instead we keep track of the longest duration that has succeeded for each
    role (AWS denies requests if the duration is higher than the allowed max).
    If one exists, we return it. If not, we return None. If the user doesn't
    like the cached max duration, they can correct it by explicitly passing a
    duration.

    [1]: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use.html#id_roles_use_view-role-max-session
    """

    cache = load_cache()
    if not cache:
        return 0

    if "MaxSessionDuration" not in cache:
        log.debug("No max durations in cache.")
        return 0

    if role_arn not in cache["MaxSessionDuration"]:
        log.debug(f"No max duration found for role {role_arn} in cache.")
        return 0

    return cache["MaxSessionDuration"][role_arn]


def assume_profile_role(role_profile, session_name="", session_duration=0):
    """Assume role described by role_profile and return the auth response."""

    # Get local profile config
    config = Session(profile=role_profile).get_scoped_config()

    # Construct assume role request
    assert "role_arn" in config, f"{role_profile} does not have role_arn."
    role_arn = config["role_arn"]
    rq = {
        "RoleArn": role_arn,
        "RoleSessionName": session_name or get_default_session_name(),
        # "DurationSeconds": 28800 # get_max_duration(role_arn)
    }

    # Specify duration if one was given
    if not session_duration:
        best_max = get_max_duration(role_arn)
        dt = timedelta(seconds=best_max)
        log.debug(f"Using duration of {humanize.naturaldelta(dt)} based on cache.")
        session_duration = best_max

    if session_duration:
        rq["DurationSeconds"] = session_duration
    else:
        log.debug(f"No session duration specified, letting AWS choose a default.")

    # Add MFA token if needed
    if "mfa_serial" in config:
        rq["SerialNumber"] = config["mfa_serial"]
        rq["TokenCode"] = questionary.text("Enter MFA code:").ask()

    # Log request before making it
    log.debug(f"Auth request:\n{json.dumps(rq, indent=4)}")

    # If source_profile is given, we should use it instead of the default profile
    source_profile = config.get("source_profile")
    log.info(f"Using source profile: {source_profile}")

    # Get auth token
    session = boto3.Session(profile_name=source_profile)
    sts = session.client("sts")
    response = sts.assume_role(**rq)

    # Cache session duration
    if session_duration:
        cache_max_duration(role_arn, session_duration)

    # Log auth token
    resp_str = json.dumps(response, indent=4, default=lambda o: str(o))
    log.debug(f"Auth response:\n{resp_str}")

    # Log expiration date
    local_exp = response["Credentials"]["Expiration"].astimezone()
    remaining = humanize.naturaldelta(local_exp - datetime.now(pytz.utc))
    log.info(f"The token will expire after {remaining} on {local_exp}")

    return response


def load_cache():
    # Default empty cache that will be returned if no valid cache found
    default = {}

    p = Path(CACHE_FILE)
    log.debug(f"Looking for cache file at: {p}")
    if not p.exists():
        log.debug("No cache file found.")
        return default

    log.debug("Found cache.")
    try:
        cache = json.loads(p.read_text())
    except JSONDecodeError:
        # When the file is corrupted, it's usually because the previous write failed
        newp = p.with_name("corrupt.json")
        msg = (
            f"Cache is corrupt. It will be moved to {newp} and the program "
            f"will proceed as if you had no cache."
        )
        log.warning(msg)
        return {}

    return cache


def write_cache(data):
    p = Path(CACHE_FILE)

    pdir = p.parent
    if not pdir.exists():
        log.debug(f"Creating directory: {pdir}")
        pdir.mkdir(parents=True)

    log.debug(f"Writing cache to: {p}")
    p.write_text(json.dumps(data, indent=4))


def cache_max_duration(role_arn, session_duration):
    cache = load_cache()
    max_durations = cache.setdefault("MaxSessionDuration", {})
    if session_duration > max_durations.get(role_arn, 0):
        max_durations[role_arn] = session_duration
        write_cache(cache)


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
