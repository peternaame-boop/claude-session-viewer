import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../tools" as Tools
import "../context" as Context

Item {
    id: aiRoot

    property string modelName: ""
    property string status: ""
    property int toolCount: 0
    property int tokenCount: 0
    property int duration: 0
    property real cost: 0.0
    property string aiText: ""
    property var toolExecutions: []
    property var contextStats: null
    property var processes: []

    property bool expanded: false

    implicitHeight: aiCard.height
    implicitWidth: parent ? parent.width : 400

    Rectangle {
        id: aiCard
        anchors.left: parent.left
        width: Math.min(contentCol.implicitWidth + Kirigami.Units.gridUnit * 2,
                       parent.width * 0.92)
        height: contentCol.implicitHeight + Kirigami.Units.gridUnit
        radius: Kirigami.Units.cornerRadius
        color: Kirigami.Theme.backgroundColor
        border.color: Kirigami.Theme.separatorColor
        border.width: 1

        ColumnLayout {
            id: contentCol
            anchors {
                fill: parent
                margins: Kirigami.Units.smallSpacing * 2
            }
            spacing: Kirigami.Units.smallSpacing

            // Header row (always visible, clickable)
            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                // Model icon
                Kirigami.Icon {
                    source: "dialog-messages"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    opacity: 0.7
                }

                // Model name
                QQC2.Label {
                    text: {
                        let name = aiRoot.modelName;
                        if (name.includes("opus")) return "Claude (Opus)";
                        if (name.includes("sonnet")) return "Claude (Sonnet)";
                        if (name.includes("haiku")) return "Claude (Haiku)";
                        return name || "Claude";
                    }
                    font.weight: Font.Bold
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }

                // Status badge
                Rectangle {
                    visible: aiRoot.status !== "" && aiRoot.status !== "complete"
                    width: statusLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                    height: statusLabel.implicitHeight + 4
                    radius: height / 2
                    color: {
                        switch (aiRoot.status) {
                            case "error": return Kirigami.Theme.negativeBackgroundColor;
                            case "interrupted": return Kirigami.Theme.neutralBackgroundColor;
                            case "in_progress": return Kirigami.Theme.positiveBackgroundColor;
                            default: return "transparent";
                        }
                    }
                    QQC2.Label {
                        id: statusLabel
                        anchors.centerIn: parent
                        text: aiRoot.status
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        font.capitalization: Font.Capitalize
                    }
                }

                // Text preview when collapsed
                QQC2.Label {
                    visible: !aiRoot.expanded && aiRoot.aiText !== ""
                    Layout.fillWidth: true
                    text: "\u2014 " + aiRoot.aiText.substring(0, 120).replace(/\n/g, " ")
                    elide: Text.ElideRight
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.5
                    maximumLineCount: 1
                }

                Item { Layout.fillWidth: aiRoot.expanded || aiRoot.aiText === "" }

                // Context badge
                Context.ContextBadge {
                    contextStats: aiRoot.contextStats
                    totalTokens: aiRoot.contextStats ? (aiRoot.contextStats.totalEstimatedTokens || 0) : 0
                    visible: totalTokens > 0
                }

                // Metric pills
                QQC2.Label {
                    visible: aiRoot.toolCount > 0
                    text: aiRoot.toolCount + " tools"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.7
                }

                QQC2.Label {
                    visible: aiRoot.tokenCount > 0
                    text: "~" + (aiRoot.tokenCount / 1000).toFixed(1) + "k"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.7
                }

                QQC2.Label {
                    visible: aiRoot.duration > 0
                    text: (aiRoot.duration / 1000).toFixed(1) + "s"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.7
                }

                QQC2.Label {
                    visible: aiRoot.cost > 0
                    text: "$" + aiRoot.cost.toFixed(4)
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.7
                }

                // Expand/collapse icon
                Kirigami.Icon {
                    source: aiRoot.expanded ? "arrow-up" : "arrow-down"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: aiRoot.expanded = !aiRoot.expanded
                    cursorShape: Qt.PointingHandCursor
                }
            }

            // Expanded content — lazy loaded to avoid creating heavy items for collapsed chunks
            Loader {
                Layout.fillWidth: true
                active: aiRoot.expanded
                sourceComponent: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing

                    // AI response text
                    QQC2.Label {
                        Layout.fillWidth: true
                        text: aiRoot.aiText
                        wrapMode: Text.Wrap
                        textFormat: Text.MarkdownText
                        visible: aiRoot.aiText !== ""
                    }

                    // Tool executions
                    Repeater {
                        model: aiRoot.toolExecutions || []

                        Tools.ToolCard {
                            required property var modelData
                            Layout.fillWidth: true
                            toolName: modelData.toolName || ""
                            inputSummary: modelData.inputSummary || ""
                            resultSummary: modelData.resultSummary || ""
                            isError: modelData.isError || false
                            durationMs: modelData.durationMs || 0
                            inputData: modelData.inputData || ""
                            resultData: modelData.resultData || ""
                            filePath: modelData.filePath || ""
                            fileExtension: modelData.fileExtension || ""
                            syntaxDefinition: modelData.syntaxDefinition || ""
                            oldString: modelData.oldString || ""
                            newString: modelData.newString || ""
                            replaceAll: modelData.replaceAll || false
                            diffLines: modelData.diffLines || []
                            command: modelData.command || ""
                            description: modelData.description || ""
                            pattern: modelData.pattern || ""
                            content: modelData.content || ""
                            lineOffset: modelData.lineOffset || 0
                            lineLimit: modelData.lineLimit || 0
                        }
                    }

                    // Subagent processes
                    Repeater {
                        model: aiRoot.processes || []

                        Tools.SubagentItem {
                            required property var modelData
                            Layout.fillWidth: true
                            process: modelData
                        }
                    }
                }
            }
        }
    }
}
