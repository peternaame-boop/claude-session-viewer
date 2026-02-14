# Maintainer: Peter
pkgname=claude-session-viewer
pkgver=1.0.0
pkgrel=1
pkgdesc="Native KDE Plasma 6 viewer for Claude Code session logs"
arch=('any')
url="https://github.com/peterbe/claude-session-viewer"
license=('MIT')
depends=(
    'python>=3.12'
    'pyside6'
    'python-orjson'
    'python-asyncssh'
    'python-dbus-next'
    'kirigami'
    'qt6-declarative'
    'ksyntaxhighlighting'
)
makedepends=(
    'python-build'
    'python-installer'
    'python-setuptools'
    'python-wheel'
)
checkdepends=(
    'python-pytest'
    'python-pytest-qt'
)
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

check() {
    cd "$pkgname-$pkgver"
    pytest tests/ -x --ignore=tests/test_file_watcher.py
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Desktop integration
    install -Dm644 resources/org.kde.claudesessionviewer.desktop \
        "$pkgdir/usr/share/applications/org.kde.claudesessionviewer.desktop"
    install -Dm644 resources/org.kde.claudesessionviewer.metainfo.xml \
        "$pkgdir/usr/share/metainfo/org.kde.claudesessionviewer.metainfo.xml"
    install -Dm644 resources/org.kde.claudesessionviewer.notifyrc \
        "$pkgdir/usr/share/knotifications6/org.kde.claudesessionviewer.notifyrc"
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
