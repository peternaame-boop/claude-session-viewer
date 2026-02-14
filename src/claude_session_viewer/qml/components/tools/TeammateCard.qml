import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: teammateRoot

    property string memberName: ""
    property string teamName: ""
    property string memberColor: "#4A9EFF"

    Layout.fillWidth: true
    implicitHeight: 32
    radius: Kirigami.Units.cornerRadius
    color: Qt.rgba(Qt.color(teammateRoot.memberColor).r,
                   Qt.color(teammateRoot.memberColor).g,
                   Qt.color(teammateRoot.memberColor).b, 0.08)

    // Left accent border
    Rectangle {
        id: leftAccent
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        radius: Kirigami.Units.cornerRadius
        color: teammateRoot.memberColor
    }

    RowLayout {
        anchors {
            fill: parent
            leftMargin: leftAccent.width + Kirigami.Units.smallSpacing * 2
            rightMargin: Kirigami.Units.smallSpacing * 2
        }
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            source: "user"
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: Kirigami.Units.iconSizes.small
            color: teammateRoot.memberColor
        }

        QQC2.Label {
            text: teammateRoot.memberName
            font.weight: Font.Bold
            font.pointSize: Kirigami.Theme.smallFont.pointSize
        }

        QQC2.Label {
            visible: teammateRoot.teamName !== ""
            text: teammateRoot.teamName
            font.italic: true
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            opacity: 0.5
        }

        Item { Layout.fillWidth: true }
    }
}
