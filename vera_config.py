import os


def get_vera_config():
    """

    :return: dict containing vera configuration
    :rtype dict
    """
    config = dict()

    config['vera_auth_user'] = os.environ["VERA_AUTH_USER"] if os.environ["VERA_AUTH_USER"] != 'None' else None
    config['vera_auth_password'] = os.environ["VERA_AUTH_KEY"] if os.environ["VERA_AUTH_KEY"] != 'None' else None
    config['vera_ip'] = os.environ["VERA_IP"]
    config['vera_auth'] = True if os.environ["VERA_AUTH"] == "True" else False

    return config
