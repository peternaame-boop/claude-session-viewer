import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: panelRoot

    property var allContextStats: []
    property bool visible: false

    width: 300
    color: Kirigami.Theme.backgroundColor
    border.color: Kirigami.Theme.separatorColor
    border.width: 1

    // Compute session-wide totals
    property int sessionTotalTokens: {
        let total = 0;
        for (let i = 0; i < allContextStats.length; i++) {
            total += (allContextStats[i].totalEstimatedTokens || 0);
        }
        return total;
    }

    property int phaseCount: {
        let maxPhase = 0;
        for (let i = 0; i < allContextStats.length; i++) {
            let p = allContextStats[i].phaseNumber || 0;
            if (p > maxPhase) maxPhase = p;
        }
        return maxPhase;
    }

    // Aggregate injections grouped by category
    property var categoryGroups: {
        let groups = {};
        for (let i = 0; i < allContextStats.length; i++) {
            let stats = allContextStats[i];
            let injections = stats.accumulatedInjections || [];
            for (let j = 0; j < injections.length; j++) {
                let inj = injections[j];
                let cat = inj.category || "unknown";
                if (!groups[cat]) {
                    groups[cat] = { category: cat, totalTokens: 0, injections: [] };
                }
                // Avoid duplicates by injection id
                let exists = false;
                for (let k = 0; k < groups[cat].injections.length; k++) {
                    if (groups[cat].injections[k].id === inj.id) {
                        exists = true;
                        break;
                    }
                }
                if (!exists) {
                    groups[cat].totalTokens += (inj.estimatedTokens || 0);
                    groups[cat].injections.push({
                        id: inj.id,
                        displayName: inj.displayName || "",
                        path: inj.path || "",
                        estimatedTokens: inj.estimatedTokens || 0,
                        turnIndex: i
                    });
                }
            }
        }
        let result = [];
        for (let key in groups) {
            if (groups.hasOwnProperty(key)) {
                result.push(groups[key]);
            }
        }
        result.sort(function(a, b) { return b.totalTokens - a.totalTokens; });
        return result;
    }

    // Category display name mapping
    function _categoryName(key) {
        let names = {
            "claude-md": "CLAUDE.md",
            "mentioned-file": "Mentioned Files",
            "tool-output": "Tool Output",
            "thinking-text": "Thinking",
            "task-coordination": "Task Coordination",
            "user-message": "User Messages"
        };
        return names[key] || key;
    }

    // Format token count
    function _formatTokens(count) {
        if (count >= 1000000) {
            return (count / 1000000).toFixed(1) + "M";
        }
        if (count >= 1000) {
            return (count / 1000).toFixed(1) + "k";
        }
        return count.toString();
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            height: headerRow.implicitHeight + Kirigami.Units.smallSpacing * 3
            color: Qt.rgba(Kirigami.Theme.textColor.r,
                           Kirigami.Theme.textColor.g,
                           Kirigami.Theme.textColor.b, 0.04)

            RowLayout {
                id: headerRow
                anchors {
                    fill: parent
                    margins: Kirigami.Units.smallSpacing * 2
                }
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    source: "view-statistics"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                }

                QQC2.Label {
                    text: "Context Analysis"
                    font.weight: Font.Bold
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    Layout.fillWidth: true
                }

                QQC2.ToolButton {
                    icon.name: "window-close"
                    display: QQC2.AbstractButton.IconOnly
                    onClicked: panelRoot.visible = false

                    QQC2.ToolTip.text: "Close panel"
                    QQC2.ToolTip.visible: hovered
                    QQC2.ToolTip.delay: 500
                }
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        // Summary section
        Rectangle {
            Layout.fillWidth: true
            height: summaryCol.implicitHeight + Kirigami.Units.smallSpacing * 3
            color: "transparent"

            ColumnLayout {
                id: summaryCol
                anchors {
                    fill: parent
                    margins: Kirigami.Units.smallSpacing * 2
                }
                spacing: Kirigami.Units.smallSpacing / 2

                QQC2.Label {
                    text: "Session Summary"
                    font.weight: Font.DemiBold
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.7
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.Label {
                        text: "Total tokens:"
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        opacity: 0.6
                    }
                    QQC2.Label {
                        text: _formatTokens(panelRoot.sessionTotalTokens)
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        font.weight: Font.DemiBold
                        font.family: "monospace"
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.Label {
                        text: "Phases:"
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        opacity: 0.6
                    }
                    QQC2.Label {
                        text: panelRoot.phaseCount.toString()
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        font.weight: Font.DemiBold
                        font.family: "monospace"
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.Label {
                        text: "Turns tracked:"
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        opacity: 0.6
                    }
                    QQC2.Label {
                        text: panelRoot.allContextStats.length.toString()
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        font.weight: Font.DemiBold
                        font.family: "monospace"
                    }
                }
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        // Scrollable category list
        QQC2.ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff

            ColumnLayout {
                width: parent.width
                spacing: Kirigami.Units.smallSpacing

                Repeater {
                    model: panelRoot.categoryGroups

                    ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.margins: Kirigami.Units.smallSpacing * 2
                        spacing: Kirigami.Units.smallSpacing

                        // Section header
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            QQC2.Label {
                                text: _categoryName(modelData.category)
                                font.weight: Font.Bold
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                Layout.fillWidth: true
                            }

                            QQC2.Label {
                                text: _formatTokens(modelData.totalTokens)
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                font.family: "monospace"
                                opacity: 0.7
                            }
                        }

                        // Injection cards
                        Repeater {
                            model: modelData.injections

                            Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: injLayout.implicitHeight + Kirigami.Units.smallSpacing * 2
                                radius: Kirigami.Units.cornerRadius
                                color: Qt.rgba(Kirigami.Theme.textColor.r,
                                               Kirigami.Theme.textColor.g,
                                               Kirigami.Theme.textColor.b, 0.04)

                                ColumnLayout {
                                    id: injLayout
                                    anchors {
                                        fill: parent
                                        margins: Kirigami.Units.smallSpacing
                                    }
                                    spacing: 2

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        QQC2.Label {
                                            Layout.fillWidth: true
                                            text: modelData.displayName || modelData.path || modelData.id
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                                            font.family: "monospace"
                                            elide: Text.ElideMiddle
                                        }

                                        // Turn index badge
                                        Rectangle {
                                            width: turnLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                                            height: turnLabel.implicitHeight + 2
                                            radius: height / 2
                                            color: Qt.rgba(Kirigami.Theme.highlightColor.r,
                                                           Kirigami.Theme.highlightColor.g,
                                                           Kirigami.Theme.highlightColor.b, 0.2)

                                            QQC2.Label {
                                                id: turnLabel
                                                anchors.centerIn: parent
                                                text: "#" + modelData.turnIndex
                                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                                opacity: 0.7
                                            }
                                        }
                                    }

                                    QQC2.Label {
                                        text: _formatTokens(modelData.estimatedTokens) + " tokens"
                                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                                        opacity: 0.5
                                    }
                                }
                            }
                        }
                    }
                }

                // Bottom spacer
                Item {
                    Layout.fillWidth: true
                    height: Kirigami.Units.smallSpacing
                }
            }
        }
    }
}
