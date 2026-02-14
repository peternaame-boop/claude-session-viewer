import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

QQC2.Popup {
    id: popoverRoot

    property var contextStats: null
    property bool showPopover: false

    visible: showPopover
    onShowPopoverChanged: {
        if (showPopover) open(); else close();
    }
    onClosed: showPopover = false
    onOpened: showPopover = true

    width: 280
    padding: Kirigami.Units.smallSpacing * 2

    // Derive sorted categories from contextStats
    property var sortedCategories: {
        let result = [];
        if (!contextStats || !contextStats.tokensByCategory) return result;
        let cats = contextStats.tokensByCategory;
        for (let key in cats) {
            if (cats.hasOwnProperty(key)) {
                result.push({ key: key, tokens: cats[key] });
            }
        }
        result.sort(function(a, b) { return b.tokens - a.tokens; });
        return result;
    }

    property int totalTokens: contextStats ? (contextStats.totalEstimatedTokens || 0) : 0

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

    // Category icon mapping
    function _categoryIcon(key) {
        let icons = {
            "claude-md": "document-properties",
            "mentioned-file": "document-open",
            "tool-output": "run-build",
            "thinking-text": "help-about",
            "task-coordination": "view-task",
            "user-message": "user"
        };
        return icons[key] || "document-properties";
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

    background: Rectangle {
        radius: Kirigami.Units.cornerRadius
        color: Kirigami.Theme.backgroundColor
        border.color: Kirigami.Theme.separatorColor
        border.width: 1

        layer.enabled: true
        layer.effect: Item {}
    }

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Label {
                text: {
                    let phase = popoverRoot.contextStats ? (popoverRoot.contextStats.phaseNumber || 1) : 1;
                    return "Context Usage — Phase " + phase;
                }
                font.weight: Font.Bold
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            Item { Layout.fillWidth: true }

            QQC2.Label {
                text: _formatTokens(popoverRoot.totalTokens) + " total"
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                opacity: 0.7
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        // Category rows
        Repeater {
            model: popoverRoot.sortedCategories

            ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Icon {
                        source: _categoryIcon(modelData.key)
                        implicitWidth: Kirigami.Units.iconSizes.small
                        implicitHeight: Kirigami.Units.iconSizes.small
                        opacity: 0.7
                    }

                    QQC2.Label {
                        Layout.fillWidth: true
                        text: _categoryName(modelData.key)
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        elide: Text.ElideRight
                    }

                    QQC2.Label {
                        text: _formatTokens(modelData.tokens)
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        font.family: "monospace"
                        opacity: 0.7
                    }
                }

                // Percentage bar
                Rectangle {
                    Layout.fillWidth: true
                    height: 4
                    radius: 2
                    color: Qt.rgba(Kirigami.Theme.textColor.r,
                                   Kirigami.Theme.textColor.g,
                                   Kirigami.Theme.textColor.b, 0.1)

                    Rectangle {
                        width: popoverRoot.totalTokens > 0
                            ? parent.width * (modelData.tokens / popoverRoot.totalTokens)
                            : 0
                        height: parent.height
                        radius: 2
                        color: Kirigami.Theme.highlightColor
                    }
                }
            }
        }
    }
}
