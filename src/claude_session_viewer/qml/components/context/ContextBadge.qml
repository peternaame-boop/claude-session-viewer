import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: badgeRoot

    property var contextStats: null
    property int totalTokens: 0

    implicitWidth: pill.width
    implicitHeight: pill.height

    // Format token count for display
    function _formatTokens(count) {
        if (count >= 1000000) {
            return (count / 1000000).toFixed(1) + "M";
        }
        if (count >= 1000) {
            return (count / 1000).toFixed(1) + "k";
        }
        return count.toString();
    }

    // Determine badge color based on token count
    function _badgeColor() {
        let tokens = badgeRoot.totalTokens;
        if (tokens > 50000) {
            return Kirigami.Theme.negativeTextColor;
        }
        if (tokens >= 10000) {
            return Kirigami.Theme.neutralTextColor;
        }
        return Kirigami.Theme.positiveTextColor;
    }

    Rectangle {
        id: pill
        width: pillRow.implicitWidth + Kirigami.Units.smallSpacing * 3
        height: pillLabel.implicitHeight + Kirigami.Units.smallSpacing
        radius: height / 2
        color: Qt.rgba(_badgeColor().r, _badgeColor().g, _badgeColor().b, 0.15)
        border.color: Qt.rgba(_badgeColor().r, _badgeColor().g, _badgeColor().b, 0.4)
        border.width: 1
        visible: badgeRoot.totalTokens > 0

        RowLayout {
            id: pillRow
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing / 2

            Kirigami.Icon {
                source: "dialog-information"
                implicitWidth: Kirigami.Units.iconSizes.small
                implicitHeight: Kirigami.Units.iconSizes.small
                color: _badgeColor()
            }

            QQC2.Label {
                id: pillLabel
                text: _formatTokens(badgeRoot.totalTokens)
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                font.weight: Font.DemiBold
                color: _badgeColor()
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: popover.showPopover = !popover.showPopover
        }
    }

    TokenUsagePopover {
        id: popover
        contextStats: badgeRoot.contextStats
        showPopover: false
        y: pill.height + Kirigami.Units.smallSpacing
    }
}
