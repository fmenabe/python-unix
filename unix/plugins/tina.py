# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime
from hosts import  Host

STRATEGY_REGEXP = re.compile('([A-D]) \(([A-Z]*)\)')
SELECTIONS_REGEXP = re.compile('path: (.*), includes: (.*), excludes: (.*)')

class TinaError(Exception):
    pass


class TINAServer(Host):
    def __init__(self, tina_perl, scripts_dir, host=None):
        Host.__init__(self)
        if host:
            self.__dict__.update(host.__dict__)
        self.scripts = scripts_dir
        self.tina_perl = tina_perl
        self.base_cmd = '%s %s' % (self.tina_perl, self.scripts)


    def get_catalog_hosts(self, catalog, date, selections=False, volumetries=False):
        print catalog
        print date
        command = [
            '%s/conf.pl' % self.base_cmd,
            '-hosts',
            '-format csv',
            '-catalogs %s' % catalog,
            '-date %s' % date.strftime('%d/%m/%Y')
        ]
#        cmd = '%s/conf.pl -hosts -catalogs %s -format csv -date %s' % (
#            self.base_cmd,
#            catalog,
#            date.strftime('%d/%m/%Y')
#        )
        status, stdout, stderr = self.execute(' '.join(command))
        if not status:
            raise TinaError(stderr)

        datas = {}
        previous_host = ''
        for line in stdout.split('\n')[2:-2]:
            line_split = line.split('|')
            (
                hostname,
                enable,
                strategy,
                fulls_schedule,
                fulls_pools,
                incrs_schedule,
                incrs_pools,
            ) = line_split[:7]
            if hostname == '':
                hostname = previous_hostname
            else:
                previous_hostname = hostname

            enabled = True if enable == 'x' else False
            strategy_conf = {
                'nfs': False,
                'fulls': {
                    'enabled': False,
                    'synthetic': False,
                    'pools': fulls_pools.split(','),
                    'schedule': fulls_schedule
                },
                'incrs': {
                    'enabled': False,
                    'pools': incrs_pools.split(','),
                    'schedule': incrs_schedule
                }
            }
            if selections and volumetries:
                selections = SELECTIONS_REGEXP.search(line_split[7]).groups()
                strategy_conf.setdefault('selections', selections)
                volumetries = line_split[8:]
                strategy_conf.setdefault('volumetries', volumetries)
            elif selections:
                print line_split[6]
                selections = SELECTIONS_REGEXP.search(line[6]).groups()
                print selections
                strategy_conf.setdefault('selections', selections)
            elif volumetries:
                volumetries = line_split[7:]
                strategy_conf.setdefault('volumetries', volumetries)

            try:
                (
                    strategy_name,
                    strategy_conf_params
                ) = STRATEGY_REGEXP.search(strategy).groups()
            except AttributeError:
                pass

            for param in strategy_conf_params:
                if param == 'F':
                    strategy_conf['fulls']['enable'] = True
                elif param == 'S':
                    strategy_conf['fulls']['synthetic'] = True
                elif param == 'N':
                    strategy_conf['nfs'] = True
                elif param == 'I':
                    strategy_conf['incrs']['enable'] = True

            datas.setdefault(hostname, {'enabled': enable, 'strategies': {}})
            datas[hostname]['strategies'].setdefault(strategy_name, strategy_conf)

        print datas
        return datas


    def get_hosts(self, catalogs, date=datetime.today(), selections=False, volumetries=False):
        datas = {}
        for catalog_name in catalogs:
            hosts_conf = self.get_catalog_hosts(catalog_name, date, selections, volumetries)


    """
    def get_hosts(self, catalogs):
        hosts_cmd = '%s %s/conf.pl -hosts -format csv -catalogs %s -date 13/01/2012' % (
            self.tina_perl,
            self.scripts,
            ','.join(catalogs)
        )
        status, stdout, stderr = self.execute(hosts_cmd)
        if not status:
            return (False, stderr)

        datas = [line.split('|') for line in stdout.split('\n')[1:-1]]
        return (True, datas)


    def get_apps(self, catalogs):
        apps_cmd = '%s %s/conf.pl -apps -format csv -catalogs %s -date 13/01/2012' % (
            self.tina_perl,
            self.scripts,
            ','.join(catalogs)
        )
        status, stdout, stderr = self.execute(apps_cmd)
        if not status:
            return (False, stderr)

        datas = [line.split('|') for line in stdout.split('\n')[1:-1]]
        return (True, datas)
    """

