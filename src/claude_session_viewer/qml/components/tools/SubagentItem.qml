import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: subagentRoot

    property var process: null
    property bool expanded: false

    // Derived convenience properties
    readonly property string processId: process ? (process.id || "") : ""
    readonly property string description: process ? (process.description || "") : ""
    readonly property string subagentType: process ? (process.subagentType || "") : ""
    readonly property int durationMs: process ? (process.durationMs || 0) : 0
    readonly property int tokenCount: process ? (process.tokenCount || 0) : 0
    readonly property real costUsd: process ? (process.costUsd || 0.0) : 0.0
    readonly property bool isParallel: process ? (process.isParallel || false) : false
    readonly property string memberName: process ? (process.memberName || "") : ""
    readonly property string memberColor: process ? (process.memberColor || "") : ""
    readonly property string teamName: process ? (process.teamName || "") : ""
    readonly property var messages: process ? (process.messages || []) : []

    readonly property color accentColor: memberColor !== ""
        ? Qt.color(memberColor)
        : Kirigami.Theme.highlightColor

    Layout.fillWidth: true
    Layout.leftMargin: Kirigami.Units.gridUnit
    implicitHeight: mainColumn.implicitHeight + Kirigami.Units.smallSpacing * 2
    radius: Kirigami.Units.cornerRadius

    color: Qt.rgba(Kirigami.Theme.highlightColor.r,
                   Kirigami.Theme.highlightColor.g,
                   Kirigami.Theme.highlightColor.b, 0.05)

    // Left accent border
    Rectangle {
        id: leftBorder
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        radius: Kirigami.Units.cornerRadius
        color: subagentRoot.accentColor
    }

    ColumnLayout {
        id: mainColumn
        anchors {
            fill: parent
            leftMargin: leftBorder.width + Kirigami.Units.smallSpacing * 2
            rightMargin: Kirigami.Units.smallSpacing * 2
            topMargin: Kirigami.Units.smallSpacing
            bottomMargin: Kirigami.Units.smallSpacing
        }
        spacing: Kirigami.Units.smallSpacing

        // Header (always visible, clickable)
        MouseArea {
            Layout.fillWidth: true
            implicitHeight: headerRow.implicitHeight
            cursorShape: Qt.PointingHandCursor
            onClicked: subagentRoot.expanded = !subagentRoot.expanded

            RowLayout {
                id: headerRow
                anchors.fill: parent
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    source: subagentRoot.subagentType.toLowerCase() === "bash"
                        ? "utilities-terminal"
                        : subagentRoot.subagentType.toLowerCase() === "explore"
                            ? "search"
                            : "process-working"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    color: subagentRoot.accentColor
                }

                // Description text
                QQC2.Label {
                    Layout.fillWidth: true
                    text: subagentRoot.description || ("Subagent " + subagentRoot.processId)
                    elide: Text.ElideRight
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    font.weight: Font.DemiBold
                    maximumLineCount: 1
                }

                // Subagent type badge
                Rectangle {
                    visible: subagentRoot.subagentType !== ""
                    width: typeBadgeLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                    height: typeBadgeLabel.implicitHeight + 4
                    radius: height / 2
                    color: Qt.rgba(subagentRoot.accentColor.r,
                                   subagentRoot.accentColor.g,
                                   subagentRoot.accentColor.b, 0.15)

                    QQC2.Label {
                        id: typeBadgeLabel
                        anchors.centerIn: parent
                        text: subagentRoot.subagentType
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        color: subagentRoot.accentColor
                    }
                }

                // Parallel badge
                Rectangle {
                    visible: subagentRoot.isParallel
                    width: parallelRow.implicitWidth + Kirigami.Units.smallSpacing * 2
                    height: parallelRow.implicitHeight + 4
                    radius: height / 2
                    color: Qt.rgba(Kirigami.Theme.positiveTextColor.r,
                                   Kirigami.Theme.positiveTextColor.g,
                                   Kirigami.Theme.positiveTextColor.b, 0.15)

                    RowLayout {
                        id: parallelRow
                        anchors.centerIn: parent
                        spacing: 2

                        Kirigami.Icon {
                            source: "view-grid"
                            implicitWidth: Kirigami.Units.iconSizes.small
                            implicitHeight: Kirigami.Units.iconSizes.small
                            color: Kirigami.Theme.positiveTextColor
                        }

                        QQC2.Label {
                            text: "parallel"
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            color: Kirigami.Theme.positiveTextColor
                        }
                    }
                }

                // Duration
                QQC2.Label {
                    visible: subagentRoot.durationMs > 0
                    text: subagentRoot.durationMs >= 1000
                        ? (subagentRoot.durationMs / 1000).toFixed(1) + "s"
                        : subagentRoot.durationMs + "ms"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.5
                }

                // Token count
                QQC2.Label {
                    visible: subagentRoot.tokenCount > 0
                    text: subagentRoot.tokenCount >= 1000
                        ? (subagentRoot.tokenCount / 1000).toFixed(1) + "k"
                        : subagentRoot.tokenCount.toString()
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.5
                }

                // Expand/collapse arrow
                Kirigami.Icon {
                    source: subagentRoot.expanded ? "arrow-up" : "arrow-down"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    opacity: 0.5
                }
            }
        }

        // Expanded body
        ColumnLayout {
            Layout.fillWidth: true
            visible: subagentRoot.expanded
            spacing: Kirigami.Units.smallSpacing

            // Teammate card (if member info is present)
            TeammateCard {
                Layout.fillWidth: true
                visible: subagentRoot.memberName !== ""
                memberName: subagentRoot.memberName
                teamName: subagentRoot.teamName
                memberColor: subagentRoot.memberColor !== ""
                    ? subagentRoot.memberColor
                    : "#4A9EFF"
            }

            // Cost label
            QQC2.Label {
                visible: subagentRoot.costUsd > 0
                text: "Cost: $" + subagentRoot.costUsd.toFixed(4)
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                opacity: 0.5
            }

            // Simplified message list
            Repeater {
                model: subagentRoot.messages

                Rectangle {
                    required property var modelData
                    required property int index

                    Layout.fillWidth: true
                    implicitHeight: msgLayout.implicitHeight + Kirigami.Units.smallSpacing * 2
                    radius: Kirigami.Units.cornerRadius
                    color: modelData.role === "assistant"
                        ? Qt.rgba(Kirigami.Theme.textColor.r,
                                  Kirigami.Theme.textColor.g,
                                  Kirigami.Theme.textColor.b, 0.03)
                        : Qt.rgba(Kirigami.Theme.highlightColor.r,
                                  Kirigami.Theme.highlightColor.g,
                                  Kirigami.Theme.highlightColor.b, 0.08)

                    ColumnLayout {
                        id: msgLayout
                        anchors {
                            fill: parent
                            margins: Kirigami.Units.smallSpacing
                        }
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            // Role indicator
                            Rectangle {
                                width: roleLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                height: roleLabel.implicitHeight + 2
                                radius: height / 2
                                color: modelData.role === "assistant"
                                    ? Qt.rgba(Kirigami.Theme.highlightColor.r,
                                              Kirigami.Theme.highlightColor.g,
                                              Kirigami.Theme.highlightColor.b, 0.2)
                                    : Qt.rgba(Kirigami.Theme.textColor.r,
                                              Kirigami.Theme.textColor.g,
                                              Kirigami.Theme.textColor.b, 0.1)

                                QQC2.Label {
                                    id: roleLabel
                                    anchors.centerIn: parent
                                    text: modelData.role === "assistant" ? "Assistant" : "User"
                                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                                    font.weight: Font.DemiBold
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Tool count badge
                            Rectangle {
                                visible: (modelData.toolCount || 0) > 0
                                width: toolCountLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                height: toolCountLabel.implicitHeight + 2
                                radius: height / 2
                                color: Qt.rgba(Kirigami.Theme.textColor.r,
                                              Kirigami.Theme.textColor.g,
                                              Kirigami.Theme.textColor.b, 0.08)

                                QQC2.Label {
                                    id: toolCountLabel
                                    anchors.centerIn: parent
                                    text: (modelData.toolCount || 0) + " tools"
                                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                                    opacity: 0.6
                                }
                            }
                        }

                        // Message text (truncated)
                        QQC2.Label {
                            Layout.fillWidth: true
                            text: {
                                let t = modelData.text || "";
                                return t.length > 500 ? t.substring(0, 500) + "..." : t;
                            }
                            wrapMode: Text.Wrap
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            opacity: 0.8
                            maximumLineCount: 8
                            elide: Text.ElideRight
                            visible: (modelData.text || "") !== ""
                        }
                    }
                }
            }

            // Nested subagents (via Loader to avoid recursive instantiation)
            Repeater {
                model: process ? (process.subagents || []) : []

                Loader {
                    required property var modelData
                    Layout.fillWidth: true
                    source: "SubagentItem.qml"
                    onLoaded: item.process = modelData
                }
            }
        }
    }
}
