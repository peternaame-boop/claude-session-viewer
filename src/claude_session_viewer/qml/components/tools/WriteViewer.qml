import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.syntaxhighlighting as SH
import "../common" as Common

ColumnLayout {
    id: writeRoot

    property string filePath: ""
    property string content: ""
    property string resultData: ""
    property string syntaxDefinition: ""

    spacing: Kirigami.Units.smallSpacing

    // File path header
    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            source: "document-new"
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: Kirigami.Units.iconSizes.small
            opacity: 0.7
        }

        QQC2.Label {
            text: writeRoot.filePath
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            elide: Text.ElideMiddle
            Layout.fillWidth: true
            opacity: 0.7
        }

        // New file badge
        Rectangle {
            width: newFileLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
            height: newFileLabel.implicitHeight + 4
            radius: height / 2
            color: Kirigami.Theme.positiveBackgroundColor

            QQC2.Label {
                id: newFileLabel
                anchors.centerIn: parent
                text: "write"
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }
        }

        Common.CopyButton {
            textToCopy: writeRoot.content
        }
    }

    // Syntax-highlighted content with line number gutter
    Rectangle {
        Layout.fillWidth: true
        Layout.maximumHeight: 400
        implicitHeight: Math.min(codeFlick.contentHeight + 2, 400)
        color: Qt.rgba(0, 0, 0, 0.04)
        radius: Kirigami.Units.cornerRadius
        clip: true

        Flickable {
            id: codeFlick
            anchors.fill: parent
            anchors.margins: 1
            contentWidth: codeRow.width
            contentHeight: codeRow.height
            boundsBehavior: Flickable.StopAtBounds

            QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
            QQC2.ScrollBar.horizontal: QQC2.ScrollBar {}

            Row {
                id: codeRow
                spacing: 0

                // Line number gutter
                Text {
                    id: gutterText
                    text: writeRoot._buildLineNumbers()
                    font.family: "monospace"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: Kirigami.Theme.disabledTextColor
                    horizontalAlignment: Text.AlignRight
                    rightPadding: Kirigami.Units.smallSpacing
                    leftPadding: Kirigami.Units.smallSpacing
                    topPadding: writeEdit.topPadding
                }

                // Gutter separator
                Rectangle {
                    width: 1
                    height: Math.max(gutterText.height, writeEdit.height)
                    color: Qt.rgba(Kirigami.Theme.textColor.r,
                                  Kirigami.Theme.textColor.g,
                                  Kirigami.Theme.textColor.b, 0.1)
                }

                // Code area
                TextEdit {
                    id: writeEdit
                    text: writeRoot.content
                    readOnly: true
                    font.family: "monospace"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    wrapMode: Text.NoWrap
                    selectByMouse: true
                    leftPadding: Kirigami.Units.smallSpacing
                    topPadding: 4
                    color: Kirigami.Theme.textColor

                    SH.SyntaxHighlighter {
                        textEdit: writeEdit
                        definition: writeRoot.syntaxDefinition
                    }
                }
            }
        }
    }

    function _buildLineNumbers() {
        if (writeRoot.content === "")
            return "";
        let lines = writeRoot.content.split('\n');
        let nums = [];
        for (let i = 0; i < lines.length; i++) {
            nums.push(String(i + 1));
        }
        return nums.join('\n');
    }
}
