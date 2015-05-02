"""Utilities and helper functions."""
# pylint: disable=too-many-arguments

import logging
import os
import sys

import elasticluster
import voluptuous

from bcbiovm.common import constant


class ElastiCluster(object):

    """Wrapper over the elasticluster functionalities."""

    _CONFIG = ("-c", "--config")
    _STORAGE = ("-s", "--storage")
    _VERBOSE = ("-v", "--verbose")
    _FORCE = "--force"
    _NO_SETUP = "--no-setup"
    _USE_DEFAULTS = "--yes"
    _EC = "elasticluster"
    _EC_START = "start"
    _EC_STOP = "stop"
    _EC_SSH = "ssh"
    _EC_SETUP = "setup"

    def __init__(self, config):
        self._config = None
        self._config_file = config

        self._load_config()

    def _load_config(self):
        """Load the Elasticluster configuration."""
        # TODO(alexandrucoman): Change `storage` with a constant
        storage_dir = os.path.join(os.path.dirname(self._config_file),
                                   "storage")
        try:
            self._config = elasticluster.conf.Configurator.fromConfig(
                self._config_file, storage_dir)
        except voluptuous.Error:
            # FIXME(alexandrucoman): Raise InvalidConfig
            return None

    def get_config(self, cluster_name=None):
        """Get the config."""
        if not cluster_name:
            return self._config

        if cluster_name in self._config.cluster_conf:
            return self._config.cluster_conf[cluster_name]

        # FIXME(alexandrucoman): Raise InvalidCluster exception
        return None

    @classmethod
    def _add_common_options(cls, command, config=None, verbose=None):
        """Add common options to the command line."""
        if config:
            # Add `--config config_file` to the command
            command.extend([cls._CONFIG[1], config])

        if verbose:
            # Add `--verbose` to the command
            command.append(cls._VERBOSE[1])

    @classmethod
    def _check_command(cls, command):
        """Check if all the required information are present in
        the command line.

        Note:
            If the storage or the config is missing they will be added.
        """
        # Ckeck if received command contains '-s' or '--storage'
        if cls._STORAGE[0] not in command and cls._STORAGE[1] not in command:
            # Insert `--storage storage_path` to the command
            for argument in (constant.PATH.EC_STORAGE, cls._STORAGE[1]):
                command.insert(1, argument)

            # Notes: Clean up the old storage directory in order to avoid
            #        consistent errors.
            std_args = [arg for arg in command if not arg.startswith('-')]
            if len(std_args) >= 3 and std_args[1] == "start":
                pickle_file = (constant.PATH.PICKLE_FILE %
                               {"cluster": std_args[2]})
                if os.path.exists(pickle_file):
                    os.remove(pickle_file)

        # Check if received command contains '-c' or '--config'
        if cls._CONFIG[0] not in command and cls._CONFIG[1] not in command:
            # Insert `--config config_file` to the command
            for argument in (constant.PATH.EC_CONFIG, cls._CONFIG[1]):
                command.insert(1, argument)

    @classmethod
    def execute(cls, command, **kwargs):
        """Wrap elasticluster commands to avoid need to call separately."""
        # Note: Sets NFS client parameters for elasticluster Ansible playbook.
        #       Uses async clients which provide better throughput on
        #       reads/writes: http://goo.gl/tGrGtE (section 5.9 for tradeoffs)
        os.environ["nfsoptions"] = constant.NFS_OPTIONS
        cls._add_common_options(command, **kwargs)
        cls._check_command(command)
        sys.argv = command
        try:
            return elasticluster.main.main()
        except SystemExit as exc:
            return exc.args[0]

    @classmethod
    def start(cls, cluster, config=None, no_setup=False, verbose=False):
        """Create a cluster using the supplied configuration.

        :param cluster:   Type of cluster. It refers to a
                          configuration stanza [cluster/<name>].
        :param config:    Elasticluster config file
        :param no_setup:  Only start the cluster, do not configure it.
        :param verbose:   Increase verbosity.
        """
        command = [cls._EC, cls._EC_START, cluster]
        if no_setup:
            command.append(cls._NO_SETUP)

        return cls.execute(command, config=config, verbose=verbose)

    @classmethod
    def stop(cls, cluster, config=None, force=False, use_default=False,
             verbose=False):
        """Stop a cluster and all associated VM instances.

        :param cluster:     Type of cluster. It refers to a
                            configuration stanza [cluster/<name>].
        :param config:      Elasticluster config file
        :param force:       Remove the cluster even if not all the nodes
                            have been terminated properly.
        :param use_default: Assume `yes` to all queries and do not prompt.
        :param verbose:     Increase verbosity.
        """
        command = [cls._EC, cls._EC_STOP, cluster]
        if force:
            command.append(cls._FORCE)
        if use_default:
            command.append(cls._USE_DEFAULTS)

        return cls.execute(command, config=config, verbose=verbose)

    @classmethod
    def setup(cls, cluster, config=None, verbose=False):
        """Configure the cluster.

        :param cluster:     Type of cluster. It refers to a
                            configuration stanza [cluster/<name>].
        :param config:      Elasticluster config file
        :param verbose:     Increase verbosity.
        """
        command = [cls._EC, cls._EC_SETUP, cluster]
        return cls.execute(command, config=config, verbose=verbose)

    @classmethod
    def ssh(cls, cluster, config=None, ssh_args=None, verbose=False):
        """Connect to the frontend of the cluster using the `ssh` command.

        :param cluster:     Type of cluster. It refers to a
                            configuration stanza [cluster/<name>].
        :param config:      Elasticluster config file
        :ssh_args:          SSH command.
        :param verbose:     Increase verbosity.

        Note:
            If the ssh_args are provided the command will be executed on
            the remote machine instead of opening an interactive shell.
        """
        command = [cls._EC, cls._EC_SSH, cluster]
        if ssh_args:
            command.extend(ssh_args)
        return cls.execute(command, config=config, verbose=verbose)


def get_logger(name=constant.LOG.NAME, format_string=None):
    """Obtain a new logger object.

    :param name:          the name of the logger
    :param format_string: the format it will use for logging.

    If it is not given, the the one given at command
    line will be used, otherwise the default format.
    """
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        format_string or constant.LOG.FORMAT)

    if not logger.handlers:
        # If the logger wasn't obtained another time,
        # then it shouldn't have any loggers

        if constant.LOG.FILE:
            file_handler = logging.FileHandler(constant.LOG.FILE)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

    logger.setLevel(constant.LOG.LEVEL)
    return logger
