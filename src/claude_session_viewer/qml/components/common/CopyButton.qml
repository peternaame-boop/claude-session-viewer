import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

QQC2.ToolButton {
    id: copyBtn

    property string textToCopy: ""
    property bool copied: false

    icon.name: copied ? "dialog-ok-apply" : "edit-copy"
    display: QQC2.AbstractButton.IconOnly

    QQC2.ToolTip.text: copied ? "Copied!" : "Copy to clipboard"
    QQC2.ToolTip.visible: hovered
    QQC2.ToolTip.delay: 500

    onClicked: {
        if (textToCopy !== "") {
            // Use Qt clipboard
            let clipboard = Qt.createQmlObject(
                'import QtQuick; TextEdit { visible: false }',
                copyBtn, "clipboard_helper"
            );
            clipboard.text = textToCopy;
            clipboard.selectAll();
            clipboard.copy();
            clipboard.destroy();

            copied = true;
            copyTimer.restart();
        }
    }

    Timer {
        id: copyTimer
        interval: 2000
        onTriggered: copyBtn.copied = false
    }
}
