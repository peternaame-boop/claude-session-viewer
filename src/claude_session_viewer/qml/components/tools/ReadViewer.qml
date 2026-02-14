import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.syntaxhighlighting as SH
import "../common" as Common

ColumnLayout {
    id: readRoot

    property string filePath: ""
    property string resultData: ""
    property string syntaxDefinition: ""
    property int lineOffset: 0
    property int lineLimit: 0

    spacing: Kirigami.Units.smallSpacing

    // File path header
    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            source: "document-open"
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: Kirigami.Units.iconSizes.small
            opacity: 0.7
        }

        QQC2.Label {
            text: readRoot.filePath
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            elide: Text.ElideMiddle
            Layout.fillWidth: true
            opacity: 0.7
        }

        // Line range badge
        QQC2.Label {
            visible: readRoot.lineOffset > 0 || readRoot.lineLimit > 0
            text: {
                if (readRoot.lineOffset > 0 && readRoot.lineLimit > 0)
                    return "L" + readRoot.lineOffset + "-" + (readRoot.lineOffset + readRoot.lineLimit);
                if (readRoot.lineOffset > 0)
                    return "from L" + readRoot.lineOffset;
                if (readRoot.lineLimit > 0)
                    return readRoot.lineLimit + " lines";
                return "";
            }
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            opacity: 0.5
        }

        Common.CopyButton {
            textToCopy: readRoot.resultData
        }
    }

    // Code content with syntax highlighting and line number gutter
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
                    text: readRoot._buildLineNumbers()
                    font.family: "monospace"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: Kirigami.Theme.disabledTextColor
                    horizontalAlignment: Text.AlignRight
                    rightPadding: Kirigami.Units.smallSpacing
                    leftPadding: Kirigami.Units.smallSpacing
                    topPadding: codeEdit.topPadding
                }

                // Gutter separator
                Rectangle {
                    width: 1
                    height: Math.max(gutterText.height, codeEdit.height)
                    color: Qt.rgba(Kirigami.Theme.textColor.r,
                                  Kirigami.Theme.textColor.g,
                                  Kirigami.Theme.textColor.b, 0.1)
                }

                // Code area
                TextEdit {
                    id: codeEdit
                    text: readRoot.resultData
                    readOnly: true
                    font.family: "monospace"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    wrapMode: Text.NoWrap
                    selectByMouse: true
                    leftPadding: Kirigami.Units.smallSpacing
                    topPadding: 4
                    color: Kirigami.Theme.textColor

                    SH.SyntaxHighlighter {
                        textEdit: codeEdit
                        definition: readRoot.syntaxDefinition
                    }
                }
            }
        }
    }

    function _buildLineNumbers() {
        if (readRoot.resultData === "")
            return "";
        let lines = readRoot.resultData.split('\n');
        let start = readRoot.lineOffset > 0 ? readRoot.lineOffset : 1;
        let nums = [];
        for (let i = 0; i < lines.length; i++) {
            nums.push(String(start + i));
        }
        return nums.join('\n');
    }
}
