import os, subprocess, dotbot
from enum import Enum

class PkgStatus(Enum):
    UP_TO_DATE = 'Already up to date'
    INSTALLED = 'Newly installed'

    NOT_FOUND = 'Not found'
    NOT_SURE = 'Could not determine'

class AptGet(dotbot.Plugin):
    _directive = 'apt-get'

    def __init__(self, context):
        super(AptGet, self).__init__(self)
        self._context = context
        self._strings = {}
        self._strings[PkgStatus.UP_TO_DATE] = "is already the newest"
        self._strings[PkgStatus.INSTALLED] = ""
        self._strings[PkgStatus.NOT_FOUND] = "Unable to locate package"

    def can_handle(self, directive):
        return directive == self._directive

    def handle(self, directive, data):
        if directive != self._directive:
            raise ValueError('Apt-get cannot handle directive %s' %
                directive)
        return self._process(data)

    def _process(self, packages):
        defaults = self._context.defaults().get('apt-get', {})
        results = {}
        successful = [PkgStatus.UP_TO_DATE, PkgStatus.INSTALLED]

        # apt-get update
        self._update_index()

        for pkg in packages:
            pkgName = ""
            if isinstance(pkg, dict):
                self._log.error('Incorrect format')
            elif isinstance(pkg, list):
                pkgName = pkg[0]
                ppa = pkg[1] if len(pkg) > 1 else None
	        self._log.lowinfo("Adding PPA: '{}'".format(ppa))
                self._add_ppa(ppa)
            else:
                pkgName = pkg
	    self._log.lowinfo("Handling package: '{}'...".format(pkgName))
            result = self._install(pkgName)
            results[result] = results.get(result, 0) + 1
            if result not in successful:
                self._log.error("Could not install package: '{}'".format(pkgName))
	    elif result == PkgStatus.UP_TO_DATE:
	    	self._log.info("Package is already up to date: '{}'".format(pkgName))
	    elif result == PkgStatus.INSTALLED:
		self._log.info("Installed package: '{}'".format(pkgName))


        if all([result in successful for result in results.keys()]):
            self._log.info('All packages installed successfully')
            success = True
        else:
            success = False

        for status, amount in results.items():
            log = self._log.info if status in successful else self._log.error
            log('{} {}'.format(amount ,status.value))

        return success

    def _update_index(self):
        cmd = 'apt-get update'
        process = subprocess.Popen(cmd, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        out = process.stdout.read()
        process.stdout.close()

    def _add_ppa(self, ppa):
        cmd = 'add-apt-repository -y ppa:{}'.format(ppa)
        process = subprocess.Popen(cmd, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        out = process.stdout.read()
        process.stdout.close()
        self._update_index() # apt-get update

    def _install(self, pkg):
        cmd = 'apt-get install {} -y'.format(pkg)
        process = subprocess.Popen(cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = process.stdout.read()
        process.stdout.close()

        for item in self._strings.keys():
            if out.find(self._strings[item]) >= 0:
                return item

        self._log.warn("Could not determine what happened with package {}".format(pkg))
        return PkgStatus.NOT_SURE

