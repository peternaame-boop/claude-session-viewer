import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: systemRoot

    property string systemText: ""
    property string timestamp: ""

    property bool expanded: false

    implicitHeight: systemCard.height
    implicitWidth: parent ? parent.width : 400

    Rectangle {
        id: systemCard
        anchors.left: parent.left
        width: Math.min(systemLayout.implicitWidth + Kirigami.Units.gridUnit * 2,
                       parent.width * 0.75)
        height: systemLayout.implicitHeight + Kirigami.Units.smallSpacing * 2
        radius: Kirigami.Units.cornerRadius
        color: Kirigami.Theme.backgroundColor
        opacity: 0.7

        ColumnLayout {
            id: systemLayout
            anchors {
                fill: parent
                margins: Kirigami.Units.smallSpacing * 2
            }
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    source: "dialog-information"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    opacity: 0.6
                }

                QQC2.Label {
                    text: "System"
                    font.weight: Font.Bold
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.6
                }

                // Preview when collapsed
                QQC2.Label {
                    visible: !systemRoot.expanded
                    Layout.fillWidth: true
                    text: "\u2014 " + systemRoot.systemText.substring(0, 100).replace(/\n/g, " ")
                    elide: Text.ElideRight
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.4
                    maximumLineCount: 1
                }

                Item { Layout.fillWidth: systemRoot.expanded }

                QQC2.Label {
                    text: systemRoot.timestamp ? new Date(systemRoot.timestamp).toLocaleTimeString(Qt.locale(), "HH:mm") : ""
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.5
                    visible: systemRoot.timestamp !== ""
                }

                Kirigami.Icon {
                    source: systemRoot.expanded ? "arrow-up" : "arrow-down"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    opacity: 0.5
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: systemRoot.expanded = !systemRoot.expanded
                    cursorShape: Qt.PointingHandCursor
                }
            }

            // Expanded content — lazy loaded
            Loader {
                Layout.fillWidth: true
                active: systemRoot.expanded
                sourceComponent: QQC2.Label {
                    Layout.fillWidth: true
                    text: systemRoot.systemText
                    wrapMode: Text.Wrap
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.7
                }
            }
        }
    }
}
