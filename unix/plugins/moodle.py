import os
import re
from kvm import UbuntuVM

CONFIG_REGEXP = {
    'dbhost': re.compile("^\$CFG->dbhost\s+=.*$"),
    'dbname': re.compile("^\$CFG->dbname\s+=.*$"),
    'dbuser': re.compile("^\$CFG->dbuser\s+=.*$"),
    'dbpass': re.compile("^\$CFG->dbpass\s+=.*$"),
    'wwwroot': re.compile("^\$CFG->wwwroot\s+=.*$"),
    'dirroot': re.compile("^\$CFG->dirroot\s+=.*$"),
    'dataroot': re.compile("^\$CFG->dataroot\s+=.*$")
}
NFS_REGEXP = re.compile("^.*\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:.*nfs.*")


BASE_VHOST = """ServerName $URL

    DocumentRoot $ROOT
    <Directory />,
        Options FollowSymLinks
        AllowOverride None
    </Directory>
    <Directory $ROOT>
        Options -Indexes FollowSymLinks
        AllowOverride None
        DirectoryIndex index.php index.html index.htm
        Order allow,deny
        allow from all
    </Directory>
"""

HTTP_VHOST = """<VirtualHost *:80>
    %s
    ErrorLog /var/log/apache2/$NAME_error.log
    LogLevel warn
    CustomLog /var/log/apache2/$NAME_access.log combined
</VirtualHost>
""" % BASE_VHOST

HTTPS_VHOST = """<VirtualHost *:443>
    %s
    SSLEngine On
    SSLCertificateFile $CRT
    SSLCertificateKeyFile $KEY
    $CHCRT

    ErrorLog /var/log/apache2/$NAME_error-ssl.log
    LogLevel warn
    CustomLog /var/log/apache2/$NAME_access-ssl.log combined
</VirtualHost>
""" % BASE_VHOST


class MoodleVM(UbuntuVM):
    def __init__(self, name, parent, plateforms, disk=''):
        UbuntuVM.__init__(self, name, parent, disk)
        self.plateforms = plateforms
        self.nfs_config = {}


    def set_apache_conf(self):
        apache_root = os.path.join(self.mounted_lvs[0], 'etc', 'apache2')
        available_sites = os.path.join(apache_root, 'sites-available')
        enabled_sites = os.path.join(apache_root, 'sites-enabled')
        # Disable all sites
        for filename in self.parent.listdir(enabled_sites):
            filepath = os.path.join(enabled_sites, filename)
            self.parent.rm(filepath)

        errors = []
        for plateform, config in self.plateforms.iteritems():
            site_filepath = os.path.join(available_sites, plateform)
            enaled_path = os.path.join(enabled_sites, plateform)
            content = HTTP_VHOST
            content = content.replace("$URL", config['url'])
            content = content.replace("$ROOT", config['root'])
            content = content.replace('$NAME', plateform)
            if 'ssl' in config:
                ssl_config = config['ssl']
                ssl_vhost = HTTPS_VHOST
                ssl_vhost = ssl_vhost.replace('$URL', config['url'])
                ssl_vhost = ssl_vhost.replace('$ROOT', config['root'])
                ssl_vhost = ssl_vhost.replace('$NAME', plateform)
                ssl_vhost = ssl_vhost.replace('$CRT', ssl_config['crt'])
                ssl_vhost = ssl_vhost.replace('$KEY', ssl_config['key'])
                if 'chcrt' in ssl_config:
                    ssl_vhost = ssl_vhost.replace(
                        '$CHCRT',
                        "SSLCertificateChainFile %s" % ssl_config['chcrt']
                    )
                else:
                    ssl_vhost = ssl_vhost.replace('$CHCRT', '')
                content += "\n%s" % ssl_vhost

            output = self.parent.write(site_filepath, content)
            if not output[0]:
                errors.append(
                    "Unable to write configuration for plateform '%s': %s" % (
                        plateform,
                        output[2]
                    )
                )

            src_link = '/etc/apache2/sites-available/%s' % plateform
            dest_link = '/etc/apache2/sites-enabled/%s' % plateform
            output = self.parent.execute('chroot %s ln -s %s %s' %
                (self.mounted_lvs[0], src_link, dest_link)
            )
            if not output[0]:
                errors.append(
                    "Unable to activate site '%s': %s" % (plateform, output[2])
                )

        return (True, '', '\n'.join(errors))


    def set_moodle_conf(self):
        errors = []
        for plateform, config in self.plateforms.iteritems():
            root = '/var/www/moodle-%s' % plateform if not 'root' in config else config['root']
            if not 'moodledatas' in config:
                datas = '/var/moodledatas/%s' % plateform
            else:
                datas = config['moodledatas']
            ssl = True if 'ssl' in config and config['ssl'] else False
            url = 'https://%s' % config['url'] if ssl else 'http://%s' % config['url']
            db_config = config['database']

            config_file = os.path.join(self.mounted_lvs[0], root[1:], 'config.php')
            try:
                lines = self.parent.readlines(config_file)
            except IOError, oserr:
                errors.append(
                    "Unable to read configuration file for plateforme '%s': %s" % (
                        plateform,
                        oserr
                    )
                )
                continue

            new_content = []
            for line in lines:
                if CONFIG_REGEXP['dbhost'].match(line):
                    new_content.append("$CFG->dbhost    = '%s';" % db_config['host'])
                elif CONFIG_REGEXP['dbname'].match(line):
                    new_content.append("$CFG->dbname    = '%s';" % db_config['name'])
                elif CONFIG_REGEXP['dbuser'].match(line):
                    new_content.append("$CFG->dbuser    = '%s';" % db_config['user'])
                elif CONFIG_REGEXP['dbpass'].match(line):
                    new_content.append("$CFG->dbpass    = '%s';" % db_config['password'])
                elif CONFIG_REGEXP['wwwroot'].match(line):
                    new_content.append("$CFG->wwwroot   = '%s';" % url)
                elif CONFIG_REGEXP['dirroot'].match(line):
                    new_content.append("$CFG->dirroot   = '%s';" % root)
                elif CONFIG_REGEXP['dataroot'].match(line):
                    new_content.append("$CFG->dataroot  = '%s';" % datas)
                else:
                    new_content.append(line)

            output = self.parent.write(config_file, '\n'.join(new_content))
            if not output[0]:
                errors.append("Unable to write config file for plateform '%s': %s" % (
                    plateform,
                    output[2]
                ))

        return (True, '', '\n'.join(errors))


    def set_nfs(self):
        fstab_file = os.path.join(self.mounted_lvs[0], 'etc', 'fstab')
        try:
            content = self.parent.readlines(fstab_file)
        except IOError as ioerr:
            return (False, '', 'Unable to read fstab file: %s' % ioerr)

        new_content = []
        for line in content:
            if not NFS_REGEXP.match(line):
                new_content.append(line)

        if self.nfs_config:
            new_content.append('')
            for san_ip, vol_config in self.nfs_config.iteritems():
                for vol_path, vol_mountpoint in vol_config.iteritems():
                    new_content.append('\t'.join((
                        ':'.join((san_ip, vol_path)),
                        vol_mountpoint,
                        'nfs',
                        'nfsvers=3,rw,auto',
                        '0',
                        '0'
                    )))

        return self.parent.write(fstab_file, '\n'.join(new_content))
