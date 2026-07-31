Name:           aurynk
Version:        1.3.1
Release:        1%{?dist}
Summary:        Android Device Manager for Linux
License:        GPL-3.0-or-later
URL:            https://github.com/IshuSinghSE/aurynk
Source0:        https://github.com/IshuSinghSE/aurynk/archive/v%{version}/aurynk-%{version}.tar.gz

BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  python3
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  pkgconfig
BuildRequires:  libgtk-4-dev
BuildRequires:  libadwaita-1-dev
BuildRequires:  python3-gobject
BuildRequires:  python3-qrcode
BuildRequires:  python3-zeroconf
BuildRequires:  python3-pyudev
BuildRequires:  android-tools
BuildRequires:  libglib2.0-devel

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita-1
Requires:       python3-qrcode
Requires:       python3-zeroconf
Requires:       python3-pyudev
Requires:       android-tools

%description
Aurynk is a modern Android device manager for Linux that allows you to
wirelessly pair and manage your Android devices using ADB (Android Debug Bridge).

Features:
 * Wireless pairing via QR code
 * Device information and specifications
 * Screenshot capture
 * Screen mirroring via scrcpy
 * Modern GTK4/libadwaita interface
 * Easy device management

%prep
%autosetup

%build
meson setup builddir --prefix=/usr
ninja -C builddir

%install
DESTDIR=%{buildroot} ninja -C builddir install

%files
%{_bindir}/aurynk
/usr/lib/python3/dist-packages/aurynk/
%{_datadir}/applications/io.github.IshuSinghSE.aurynk.desktop
%{_datadir}/metainfo/io.github.IshuSinghSE.aurynk.metainfo.xml
%{_datadir}/icons/hicolor/*/apps/io.github.IshuSinghSE.aurynk*.png
%{_datadir}/icons/hicolor/scalable/apps/io.github.IshuSinghSE.aurynk.svg
%{_datadir}/aurynk/
%{_datadir}/locale/*/LC_MESSAGES/aurynk.mo
%license LICENSE
%doc README.md CHANGELOG.md

%changelog
* Mon Jul 29 2024 IshuSinghSE <ishu.111636@yahoo.com> - 1.3.1-1
- Initial RPM package release