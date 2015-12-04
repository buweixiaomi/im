# (C) 2012-2013, Michael DeHaan, <michael.dehaan@gmail.com>

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

# Miguel: Version simplificada, eliminado el lock "sospechoso"

import ansible.utils
import sys
import datetime
import logging

def display(msg, color=None, stderr=False, screen_only=False, log_only=False, runner=None, output=sys.stdout):
    if not log_only:
        msg2 = msg
        if isinstance(output, logging.Logger):
            output.info(msg2)
        else:
            print >>output, msg2

class AggregateStats(object):
    ''' holds stats about per-host activity during playbook runs '''

    def __init__(self):

        self.processed   = {}
        self.failures    = {}
        self.ok          = {}
        self.dark        = {}
        self.changed     = {}
        self.skipped     = {}

    def _increment(self, what, host):
        ''' helper function to bump a statistic '''

        self.processed[host] = 1
        prev = (getattr(self, what)).get(host, 0)
        getattr(self, what)[host] = prev+1

    def compute(self, runner_results, setup=False, poll=False, ignore_errors=False):
        ''' walk through all results and increment stats '''

        for (host, value) in runner_results.get('contacted', {}).iteritems():
            if not ignore_errors and (('failed' in value and bool(value['failed'])) or
                ('rc' in value and value['rc'] != 0)):
                self._increment('failures', host)
            elif 'skipped' in value and bool(value['skipped']):
                self._increment('skipped', host)
            elif 'changed' in value and bool(value['changed']):
                if not setup and not poll:
                    self._increment('changed', host)
                self._increment('ok', host)
            else:
                if not poll or ('finished' in value and bool(value['finished'])):
                    self._increment('ok', host)

        for (host, value) in runner_results.get('dark', {}).iteritems():
            self._increment('dark', host)


    def summarize(self, host):
        ''' return information about a particular host '''

        return dict(
            ok          = self.ok.get(host, 0),
            failures    = self.failures.get(host, 0),
            unreachable = self.dark.get(host,0),
            changed     = self.changed.get(host, 0),
            skipped     = self.skipped.get(host, 0)
        )

########################################################################

def banner(msg):
    str_date =  str(datetime.datetime.now())
    width = 78 - len(str_date + " - " + msg)
    if width < 3:
        width = 3
    filler = "*" * width
    return "\n%s %s " % (str_date + " - " + msg, filler)

########################################################################

class PlaybookRunnerCallbacks(object):
    ''' callbacks used for Runner() from /usr/bin/ansible-playbook '''

    def __init__(self, stats, verbose=ansible.utils.VERBOSITY, output=sys.stdout):
        self.output = output
        self.verbose = verbose
        self.stats = stats
        self.has_items = False
        self.last_host = None

    def _add_host(self, host):
        if self.last_host is None:
            self.has_items = False
            self.last_host = host
            msg = ', "hosts": [ { "host": "%s"' % host
        elif self.last_host != host:
            self.has_items = False
            if self.has_items:
                msg = '}}, { "host": "%s"' % host
            else:
                msg = '}, { "host": "%s"' % host 
        else:
            msg = ''
        return msg
       
    def _add_item(self, item):
        if not self.has_items:
            self.has_items = True
            msg = ', "items": [ { "item": "%s"' % item
        else:
            msg = '}, { "item": "%s"' % item
        return msg

    def on_unreachable(self, host, results):
        msg = self._add_host(host)
        item = None
        if type(results) == dict:
            item = results.get('item', None)
            msg += self._add_item(item.replace('"','\\\\\\\"'))

        msg += ', "state": "fatal", "msg": "%s"' % results.replace('"','\\\\\\\"').replace('\n','\\\\n')
        display(msg, output=self.output)

    def on_failed(self, host, results, ignore_errors=False):
        results2 = results.copy()
        results2.pop('invocation', None)

        item = results2.get('item', None)
        parsed = results2.get('parsed', True)
        module_msg = ''
        if not parsed:
            module_msg  = results2.pop('msg', None)
        stderr = results2.pop('stderr', None)
        stdout = results2.pop('stdout', None)
        returned_msg = results2.pop('msg', None)
        
        output_msg = ansible.utils.jsonify(results2)
        if returned_msg:
            output_msg += "\n %s" % returned_msg
        if not parsed and module_msg:
            output_msg += "\ninvalid output was: %s" % module_msg

        msg = self._add_host(host)

        if item:
            msg += self._add_item(item)

        msg += ', "state": "failed", "msg": "%s", "ignore_errors": "%s"' % (output_msg.replace('"','\\\\\\\"').replace('\n','\\\\n'), ignore_errors)

        if stderr:
            msg += ', "stderr": "%s"' % stderr.replace('"','\\\\\\\"').replace('\n','\\\\n')
        if stdout:
            msg += ', "stdout": "%s"' % stdout.replace('"','\\\\\\\"').replace('\n','\\\\n')

        display(msg, output=self.output)

    def on_ok(self, host, host_result):
        
        item = host_result.get('item', None)

        host_result2 = host_result.copy()
        host_result2.pop('invocation', None)
        verbose_always = host_result2.pop('verbose_always', None)
        changed = host_result.get('changed', False)
        ok_or_changed = 'ok'
        if changed:
            ok_or_changed = 'changed'

        # show verbose output for non-setup module results if --verbose is used
        msg = ''
        if (not self.verbose or host_result2.get("verbose_override",None) is not
                None) and verbose_always is None:
            if item:
                msg = self._add_host(host)
                msg += self._add_item(item.replace('"','\\\\\\\"'))
                msg += ', "state": "%s"' % ok_or_changed
            else:
                if 'ansible_job_id' not in host_result or 'finished' in host_result:
                    msg = self._add_host(host)
                    msg += ', "state": "%s"' % ok_or_changed
        else:
            # verbose ...
            if item:
                msg = self._add_host(host)
                msg += self._add_item(item)
                msg += ', "state": "%s", "msg": "%s"' % (ok_or_changed, ansible.utils.jsonify(host_result2).replace('"','\\\\\\\"').replace('\n','\\\\n'))
            else:
                if 'ansible_job_id' not in host_result or 'finished' in host_result2:
                    msg = self._add_host(host)
                    msg += ', "state": "%s", "msg": "%s"' % (ok_or_changed, ansible.utils.jsonify(host_result2).replace('"','\\\\\\\"').replace('\n','\\\\n'))

        if msg != '':
            display(msg, output=self.output)

    def on_error(self, host, err):

        item = err.get('item', None)
        msg = self._add_host(host)
        if item:
            msg += self._add_item(item.replace('"','\\\\\\\"'))

        msg += ', "state": "fatal",  msg": "%s"' % err.replace('"','\\\\\\\"').replace('\n','\\\\n')

        display(msg, output=self.output)

    def on_skipped(self, host, item=None):
        msg = self._add_host(host)
        if item:
            msg += self._add_item(item)

        msg += ', "state": "skipped"'
        display(msg, output=self.output)

    def on_no_hosts(self):
        msg = ', "state": "fatal", "msg": "FATAL: no hosts matched or all hosts have already failed"' 
        display(msg, output=self.output)

    def on_async_poll(self, host, res, jid, clock):
        pass

    def on_async_ok(self, host, res, jid):
        pass

    def on_async_failed(self, host, res, jid):
        pass

    def on_file_diff(self, host, diff):
        pass

########################################################################

class PlaybookCallbacks(object):
    ''' playbook.py callbacks used by /usr/bin/ansible-playbook '''

    def __init__(self, runner_cb, verbose=False, output=sys.stdout):

        self.verbose = verbose
        self.output=output
        self.runner_cb = runner_cb
        self.first=True

    def on_start(self):
        pass

    def on_notify(self, host, handler):
        pass

    def on_no_hosts_matched(self):
        #msg += ', "state": "fatal", "msg": "skipping: no hosts matched"' 
        #display(msg, output=self.output)
        pass

    def on_no_hosts_remaining(self):
        #msg += ', "state": "fatal", "msg": "FATAL: all hosts have already failed"' 
        #display(msg, output=self.output)
        pass

    def on_task_start(self, name, is_conditional):
        self.runner_cb.last_host=None
        if self.first:
            msg = ""
            self.first=False
        else:
            if self.runner_cb.has_items:
                msg = "}]}]}\n,"
            else:
                msg = "}]}\n,"
        msg += '\n{ "name": "%s"'  % name.replace('"','\\\\\\\"')
        if is_conditional:
            msg += '"is_conditional", "true"'
        
        self.skip_task = False
        display(msg, output=self.output)

    def on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        # We do not allow prompt for vars 
        return None

    def on_setup(self):
        self.runner_cb.last_host=None
        if self.first:
            msg = ""
            self.first=False
        else:
            if self.runner_cb.has_items:
                msg = "}]}]}\n,"
            else:
                msg = "}]}\n,"
        msg += '\n{ "name": "GATHERING FACTS"'
        display(msg, output=self.output)
        
    def on_import_for_host(self, host, imported_file):
        pass

    def on_not_import_for_host(self, host, missing_file):
        pass

    def on_play_start(self, pattern):
        pass

    def on_stats(self, stats):
        pass


