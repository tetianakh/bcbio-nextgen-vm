"""Prepare batch scripts for submitting bcbio_vm jobs.

Automates the process of preparing submission batch scripts, using the same arguments as
standard IPython runs.
"""
import os
import yaml

from bcbiovm.docker import defaults

# names that indicate we're running on a dedicated AWS queue
AWS_QUEUES = set(["cloud"])


class AWSRunConfligLoader(object):
    DEFAULTS = {
        'output_dir': '$HOME/testrun',
        'work_dir': '/mnt/S3/workdir',
        'data_dir': '$HOME/src/bcbio-nextgen/tests/data',
        'system_config':
            '$HOME/install/bcbio-vm/data/galaxy/bcbio_system.yaml',
    }
    FNAME = 'aws_run_config.yaml'

    def __init__(self):
        config = self._load()
        config = self._merge_defaults(config)
        self._config = self._expandwars(config)

    @property
    def config(self):
        return self._config.copy()

    @property
    def config_fname(self):
        return os.path.join(os.getcwd(), self.FNAME)

    def _load(self):
        if not os.path.exists(self.config_fname):
            return {}

        with open(self.config_fname, 'r') as f:
            config = yaml.load(f)
        return config

    def _merge_defaults(self, config):
        return dict(self.DEFAULTS, **config)

    def _expandwars(self, config):
        for k, v in config.iteritems():
            config[k] = os.path.expandvars(v)
        return config


_config_loader = None


def get_config():
    global _config_loader
    if _config_loader is None:
        _config_loader = AWSRunConfligLoader()
    return _config_loader.config


def _get_ipython_cmdline(args):
    """Translate arguments back into a standard bcbio_vm ipython submission command.
    """
    config = get_config()
    cmd = [
        "bcbio_vm.py",
        "--datadir=%s" % config['data_dir'],
        "ipython",
        "--systemconfig=%s" % config['system_config'],
        args.sample_config,
        args.scheduler,
        args.queue,
        "--numcores", str(args.numcores)]
    has_timelimit = False
    for resource in args.resources:
        cmd += ["-r", resource]
        if resource.startswith("timelimit"):
            has_timelimit = True
    if not has_timelimit and args.queue in AWS_QUEUES:
        cmd += ["-r", "timelimit=0"]
    for opt_arg in ["timeout", "retries", "tag", "tmpdir", "fcdir", "systemconfig"]:
        if getattr(args, opt_arg):
            cmd += ["--%s" % opt_arg, str(getattr(args, opt_arg))]
    return " ".join(cmd)

def submit_script(args):
    args = defaults.update_check_args(args, "Could not prep batch scripts")
    out_file = os.path.join(os.getcwd(), "bcbio_submit.sh")
    with open(out_file, "w") as out_handle:
        out_handle.write("#!/bin/bash\n")
        out_handle.write(_get_scheduler_cmds(args) + "\n")
        out_handle.write(_get_ipython_cmdline(args) + "\n")
    print("Submission script for %s written to %s" % (args.scheduler, out_file))
    print("Start analysis with: %s %s" % (_get_submit_cmd(args.scheduler), out_file))

def _get_scheduler_cmds(args):
    cmds = {"slurm": _get_slurm_cmds,
            "sge": _get_sge_cmds,
            "lsf": _get_lsf_cmds,
            "torque": _get_torque_cmds,
            "pbspro": _get_torque_cmds}
    try:
        return cmds[args.scheduler](args)
    except KeyError:
        raise NotImplementedError("Batch script preparation for %s not yet supported" % args.scheduler)


def _get_slurm_cmds(args):
    config = get_config()
    timelimit = "0" if args.queue in AWS_QUEUES else "1-00:00:00"
    cmds = [
        "--cpus-per-task=1",
        "--mem=2000",
        "-p %s" % args.queue,
        "-t %s" % timelimit,
        "-o %s/slurm_%%j.out" % config['output_dir'],
        "-e %s/slurm_%%j.err" % config['output_dir'],
        "-D %s" % config['work_dir'],
        "-vvvv",
    ]
    for r in args.resources:
        if r.startswith("timelimit"):
            _, timelimit = r.split("=")
    if args.tag:
        cmds += ["-J %s-submit" % args.tag]
    return "\n".join("#SBATCH %s" % x for x in cmds)

def _get_sge_cmds(args):
    cmds = ["-cwd", "-j y", "-S /bin/bash"]
    if args.queue:
        cmds += ["-q %s" % args.queue]
    if args.tag:
        cmds += ["-N %s-submit" % args.tag]
    return "\n".join("#$ %s" % x for x in cmds)

def _get_lsf_cmds(args):
    cmds = ["-q %s" % args.queue, "-n 1"]
    if args.tag:
        cmds += ["-J %s-submit" % args.tag]
    return "\n".join("#BSUB %s" % x for x in cmds)

def _get_torque_cmds(args):
    cmds = ["-V", "-j oe", "-q %s" % args.queue, "-l nodes=1:ppn=1"]
    if args.tag:
        cmds += ["-N %s-submit" % args.tag]
    return "\n".join("#PBS %s" % x for x in cmds)

def _get_submit_cmd(scheduler):
    cmds = {"slurm": "sbatch",
            "sge": "qsub",
            "lsf": "bsub",
            "torque": "qsub",
            "pbspro": "qsub"}
    return cmds[scheduler]
