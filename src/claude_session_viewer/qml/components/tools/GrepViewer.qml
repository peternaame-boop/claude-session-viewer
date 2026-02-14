import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../common" as Common

ColumnLayout {
    id: grepRoot

    property string pattern: ""
    property string resultData: ""
    property string filePath: ""
    property bool isError: false

    spacing: Kirigami.Units.smallSpacing

    // Pattern header
    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            source: "search"
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: Kirigami.Units.iconSizes.small
            opacity: 0.7
        }

        // Pattern in a highlighted box
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: patternLabel.implicitHeight + Kirigami.Units.smallSpacing
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(Kirigami.Theme.highlightColor.r,
                          Kirigami.Theme.highlightColor.g,
                          Kirigami.Theme.highlightColor.b, 0.1)

            QQC2.Label {
                id: patternLabel
                anchors {
                    left: parent.left
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                    margins: Kirigami.Units.smallSpacing
                }
                text: "/" + grepRoot.pattern + "/"
                font.family: "monospace"
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                elide: Text.ElideRight
                color: Kirigami.Theme.highlightColor
            }
        }

        // Search path
        QQC2.Label {
            visible: grepRoot.filePath !== ""
            text: grepRoot.filePath
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            opacity: 0.5
            elide: Text.ElideMiddle
            Layout.maximumWidth: 150
        }

        Common.CopyButton {
            textToCopy: grepRoot.resultData
        }
    }

    // Results
    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.maximumHeight: 300
        visible: grepRoot.resultData !== ""

        QQC2.TextArea {
            text: grepRoot.resultData
            readOnly: true
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            wrapMode: Text.NoWrap

            background: Rectangle {
                color: Qt.rgba(0, 0, 0, 0.04)
                radius: Kirigami.Units.cornerRadius
            }
        }
    }

    // No results message
    QQC2.Label {
        Layout.fillWidth: true
        visible: grepRoot.resultData === "" && !grepRoot.isError
        text: "No matches found"
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        font.italic: true
        opacity: 0.5
        horizontalAlignment: Text.AlignHCenter
    }
}
