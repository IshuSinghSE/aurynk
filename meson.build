project('aurynk',
  version: '1.1.0',
  meson_version: '>= 0.59.0'
)

python = import('python')
py = python.find_installation('python3')

# Define directories
prefix = get_option('prefix')
datadir = prefix / get_option('datadir')
pkgdatadir = datadir / meson.project_name()

# Build subdirectories for data files
subdir('data')
subdir('po')

# install python package
python_dir = join_paths(get_option('prefix'), py.get_install_dir())
install_subdir('aurynk', install_dir: python_dir)

# install launcher
install_data('scripts/aurynk', install_dir: get_option('bindir'), install_mode: 'rwxr-xr-x', rename: 'aurynk')

# install tray helper script
install_data('scripts/aurynk_tray.py', install_dir: python_dir / 'scripts', install_mode: 'rwxr-xr-x')

# install udev proxy helper script
install_data('scripts/aurynk_udev_proxy.py', install_dir: get_option('bindir'), install_mode: 'rwxr-xr-x', rename: 'aurynk_udev_proxy.py')

# install systemd user service files
systemd_userdir = get_option('prefix') / 'lib' / 'systemd' / 'user'
install_data('packaging/systemd/user/aurynk-udev-proxy.service', install_dir: systemd_userdir)
install_data('packaging/systemd/user/aurynk-udev-proxy.socket', install_dir: systemd_userdir)
