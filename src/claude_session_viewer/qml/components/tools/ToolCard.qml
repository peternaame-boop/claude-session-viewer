import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: toolRoot

    // Data properties (passed from AIGroup repeater)
    property string toolName: ""
    property string inputSummary: ""
    property string resultSummary: ""
    property bool isError: false
    property int durationMs: 0
    property string inputData: ""
    property string resultData: ""
    // Rich viewer properties
    property string filePath: ""
    property string fileExtension: ""
    property string syntaxDefinition: ""
    property string oldString: ""
    property string newString: ""
    property bool replaceAll: false
    property var diffLines: []
    property string command: ""
    property string description: ""
    property string pattern: ""
    property string content: ""
    property int lineOffset: 0
    property int lineLimit: 0

    property bool expanded: false

    Layout.fillWidth: true
    implicitHeight: toolLayout.implicitHeight + Kirigami.Units.smallSpacing * 2
    radius: Kirigami.Units.cornerRadius

    color: isError
        ? Qt.rgba(Kirigami.Theme.negativeTextColor.r,
                  Kirigami.Theme.negativeTextColor.g,
                  Kirigami.Theme.negativeTextColor.b, 0.08)
        : Qt.rgba(Kirigami.Theme.textColor.r,
                  Kirigami.Theme.textColor.g,
                  Kirigami.Theme.textColor.b, 0.04)

    border.color: isError
        ? Qt.rgba(Kirigami.Theme.negativeTextColor.r,
                  Kirigami.Theme.negativeTextColor.g,
                  Kirigami.Theme.negativeTextColor.b, 0.3)
        : "transparent"
    border.width: isError ? 1 : 0

    ColumnLayout {
        id: toolLayout
        anchors {
            fill: parent
            margins: Kirigami.Units.smallSpacing * 2
        }
        spacing: Kirigami.Units.smallSpacing

        // Header — always visible, clickable
        MouseArea {
            Layout.fillWidth: true
            implicitHeight: headerRow.implicitHeight
            cursorShape: Qt.PointingHandCursor
            onClicked: toolRoot.expanded = !toolRoot.expanded

            RowLayout {
                id: headerRow
                anchors.fill: parent
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    source: toolRoot.isError ? "dialog-error" : _toolIcon(toolRoot.toolName)
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    color: toolRoot.isError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.disabledTextColor
                }

                QQC2.Label {
                    text: toolRoot.toolName
                    font.weight: Font.DemiBold
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    font.family: "monospace"
                    color: toolRoot.isError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
                }

                QQC2.Label {
                    Layout.fillWidth: true
                    text: toolRoot.inputSummary
                    elide: Text.ElideRight
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.6
                    visible: !toolRoot.expanded
                }

                QQC2.Label {
                    visible: toolRoot.durationMs > 0
                    text: toolRoot.durationMs >= 1000
                        ? (toolRoot.durationMs / 1000).toFixed(1) + "s"
                        : toolRoot.durationMs + "ms"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.5
                }

                Kirigami.Icon {
                    source: toolRoot.expanded ? "arrow-up" : "arrow-down"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    opacity: 0.5
                }
            }
        }

        // Collapsed summary
        QQC2.Label {
            Layout.fillWidth: true
            text: toolRoot.resultSummary
            elide: Text.ElideRight
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            opacity: 0.6
            visible: !toolRoot.expanded && toolRoot.resultSummary !== ""
            maximumLineCount: 1
        }

        // Expanded body — loads appropriate viewer
        Loader {
            Layout.fillWidth: true
            visible: toolRoot.expanded
            active: toolRoot.expanded

            sourceComponent: {
                let name = toolRoot.toolName.toLowerCase();
                switch (name) {
                    case "read":
                    case "glob":
                        return readViewerComponent;
                    case "edit":
                        return editViewerComponent;
                    case "write":
                    case "notebookedit":
                        return writeViewerComponent;
                    case "bash":
                        return bashViewerComponent;
                    case "grep":
                        return grepViewerComponent;
                    default:
                        return defaultViewerComponent;
                }
            }
        }
    }

    // Viewer components
    Component {
        id: readViewerComponent
        ReadViewer {
            filePath: toolRoot.filePath
            resultData: toolRoot.resultData
            syntaxDefinition: toolRoot.syntaxDefinition
            lineOffset: toolRoot.lineOffset
            lineLimit: toolRoot.lineLimit
        }
    }

    Component {
        id: editViewerComponent
        EditViewer {
            filePath: toolRoot.filePath
            oldString: toolRoot.oldString
            newString: toolRoot.newString
            replaceAll: toolRoot.replaceAll
            diffLines: toolRoot.diffLines
            resultData: toolRoot.resultData
        }
    }

    Component {
        id: writeViewerComponent
        WriteViewer {
            filePath: toolRoot.filePath
            content: toolRoot.content
            resultData: toolRoot.resultData
            syntaxDefinition: toolRoot.syntaxDefinition
        }
    }

    Component {
        id: bashViewerComponent
        BashViewer {
            command: toolRoot.command
            description: toolRoot.description
            resultData: toolRoot.resultData
            isError: toolRoot.isError
        }
    }

    Component {
        id: grepViewerComponent
        GrepViewer {
            pattern: toolRoot.pattern
            resultData: toolRoot.resultData
            filePath: toolRoot.filePath
            isError: toolRoot.isError
        }
    }

    Component {
        id: defaultViewerComponent
        DefaultViewer {
            inputData: toolRoot.inputData
            resultData: toolRoot.resultData
            isError: toolRoot.isError
        }
    }

    // Tool icon helper
    function _toolIcon(name) {
        let n = name.toLowerCase();
        if (n === "read" || n === "glob") return "document-open";
        if (n === "edit") return "document-edit";
        if (n === "write" || n === "notebookedit") return "document-new";
        if (n === "bash") return "utilities-terminal";
        if (n === "grep") return "search";
        return "run-build";
    }
}
