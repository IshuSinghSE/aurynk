project('mirage',
  version: '0.1.0',
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

# install python package
python_dir = join_paths(get_option('prefix'), py.get_install_dir())
install_subdir('mirage', install_dir: python_dir)

# install launcher
install_data('scripts/mirage', install_dir: get_option('bindir'), install_mode: 'rwxr-xr-x', rename: 'mirage')

