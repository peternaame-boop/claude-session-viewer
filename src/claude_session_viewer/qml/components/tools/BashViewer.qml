import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../common" as Common

ColumnLayout {
    id: bashRoot

    property string command: ""
    property string description: ""
    property string resultData: ""
    property bool isError: false

    spacing: Kirigami.Units.smallSpacing

    // Command header
    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        QQC2.Label {
            text: "$ "
            font.family: "monospace"
            font.weight: Font.Bold
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            opacity: 0.5
        }

        QQC2.Label {
            text: bashRoot.command
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            elide: Text.ElideRight
            Layout.fillWidth: true
            color: bashRoot.isError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
        }

        Common.CopyButton {
            textToCopy: bashRoot.resultData
        }
    }

    // Description (if provided)
    QQC2.Label {
        Layout.fillWidth: true
        visible: bashRoot.description !== ""
        text: bashRoot.description
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        font.italic: true
        opacity: 0.5
        elide: Text.ElideRight
    }

    // Output
    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.maximumHeight: 300
        visible: bashRoot.resultData !== ""

        QQC2.TextArea {
            text: bashRoot.resultData
            readOnly: true
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            wrapMode: Text.NoWrap
            color: bashRoot.isError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor

            background: Rectangle {
                color: bashRoot.isError
                    ? Qt.rgba(Kirigami.Theme.negativeTextColor.r,
                             Kirigami.Theme.negativeTextColor.g,
                             Kirigami.Theme.negativeTextColor.b, 0.05)
                    : Qt.rgba(0, 0, 0, 0.06)
                radius: Kirigami.Units.cornerRadius
            }
        }
    }
}
