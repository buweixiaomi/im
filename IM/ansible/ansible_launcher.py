# (C) 2012, Michael DeHaan, <michael.dehaan@gmail.com>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

#######################################################

# Miguel Caballer: file based on the ansible-playbook

import time
import os
import threading
import ansible.playbook
import ansible.inventory
import ansible.constants as C
from ansible import errors
from ansible import utils

from ansible_callbacks import display, AggregateStats, PlaybookCallbacks, PlaybookRunnerCallbacks

def colorize(lead, num, color):
    """ Print 'lead' = 'num' in 'color' """
    return "%s=%-4s" % (lead, str(num))

def hostcolor(host, stats, color=True):
    return "%-26s" % host

def launch_playbook(output, playbook_file, host, passwd, threads, pk_file = None, inventory_file=None, user=None, extra_vars={}):
    ''' run ansible-playbook operations '''

    # create parser for CLI options
    parser = utils.base_parser(
        constants=C,
        usage = "%prog playbook.yml",
        connect_opts=True,
        runas_opts=True,
        subset_opts=True,
        check_opts=True,
        diff_opts=True
    )

    options, _ = parser.parse_args([])

    sshpass = None
    if pk_file:
        options.private_key_file = pk_file
    else:
        sshpass = passwd
    
    if user:
        remote_user=user
    else:
        remote_user=options.remote_user

    if not os.path.exists(playbook_file):
        raise errors.AnsibleError("the playbook: %s could not be found" % playbook_file)
    if not os.path.isfile(playbook_file):
        raise errors.AnsibleError("the playbook: %s does not appear to be a file" % playbook_file)

    return_code = 0

    if inventory_file:
        inventory = ansible.inventory.Inventory(inventory_file)
    else:
        inventory = ansible.inventory.Inventory(options.inventory)
        
    inventory.subset(host)
    # let inventory know which playbooks are using so it can know the basedirs
    inventory.set_playbook_basedir(os.path.dirname(playbook_file))

    stats = AggregateStats()
    runner_cb = PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY, output=output)
    playbook_cb = PlaybookCallbacks(runner_cb, verbose=utils.VERBOSITY, output=output)

    pb = ansible.playbook.PlayBook(
        playbook=playbook_file,
        module_path=options.module_path,
        inventory=inventory,
        forks=threads,
        remote_user=remote_user,
        remote_pass=sshpass,
        callbacks=playbook_cb,
        runner_callbacks=runner_cb,
        stats=stats,
        extra_vars=extra_vars,
        private_key_file=options.private_key_file,
        only_tags=['all']
    )

    try:
        failed_hosts = []
        unreachable_hosts = []

        display('"playbook": { "file" : "%s", "tasks" : [' % playbook_file, output=output)

        pb.run()
        
        display("}]}\n]}", output=output)

        hosts = sorted(pb.stats.processed.keys())
        #display(banner("PLAY RECAP"), output=output)
        playbook_cb.on_stats(pb.stats)

        for h in hosts:
            t = pb.stats.summarize(h)
            if t['failures'] > 0:
                failed_hosts.append(h)
            if t['unreachable'] > 0:
                unreachable_hosts.append(h)

        hosts_with_errors = failed_hosts + unreachable_hosts

        if len(failed_hosts) > 0:
            return_code = 2
            display(', "state": "error", "msg": "Some nodes has failed."', output=output)
        if len(unreachable_hosts) > 0:
            return_code = 3
            display(', "state": "error", "msg": "Some nodes are unreachable"', output=output)

    except errors.AnsibleError, e:
        #display("ERROR: %s" % e, color='red', output=output)
        display(', "state": "error", "msg": "%s"' % e, output=output)
        return_code = 1

    if return_code == 0:
        display(', "state": "ok"', output=output)
    return (return_code, hosts_with_errors)


class AnsibleThread(threading.Thread):
    """
    Class to call the ansible playbooks in a Thread
    """
    def __init__(self, output, playbook_file, host = None, threads = 1, pk_file = None, passwd = None, inventory_file=None, user=None, extra_vars={}):
        threading.Thread.__init__(self)

        self.playbook_file = playbook_file
        self.host = host
        self.passwd = passwd
        self.threads = threads
        self.pk_file = pk_file
        self.inventory_file = inventory_file
        self.user = user
        self.extra_vars=extra_vars
        self.output = output
        self.results = (None, None)
        
    def run(self):
        try:
            self.results = launch_playbook(self.output, self.playbook_file, self.host, self.passwd, self.threads, self.pk_file, self.inventory_file, self.user, self.extra_vars)
        except errors.AnsibleError, e:
            display("ERROR: %s" % e, color='red', stderr=True, output=self.output)
            self.results = (1, [])
