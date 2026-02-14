import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: compactRoot

    property int tokensFreed: 0
    property int phaseNumber: 0

    implicitHeight: compactColumn.height + Kirigami.Units.largeSpacing
    implicitWidth: parent ? parent.width : 400

    ColumnLayout {
        id: compactColumn
        anchors.centerIn: parent
        width: parent.width
        spacing: 2

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            // Left gradient separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.5; color: Kirigami.Theme.separatorColor }
                    GradientStop { position: 1.0; color: Kirigami.Theme.separatorColor }
                }
            }

            // Main compact label
            QQC2.Label {
                text: {
                    if (compactRoot.tokensFreed > 0) {
                        return "Context compacted \u2014 " + (compactRoot.tokensFreed / 1000).toFixed(1) + "k tokens freed";
                    }
                    return "Context compacted";
                }
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                font.italic: true
                opacity: 0.5
                horizontalAlignment: Text.AlignHCenter
            }

            // Right gradient separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Kirigami.Theme.separatorColor }
                    GradientStop { position: 0.5; color: Kirigami.Theme.separatorColor }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }
        }

        // Phase badge (shown below when phaseNumber > 0)
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            visible: compactRoot.phaseNumber > 0
            width: phaseBadgeLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
            height: phaseBadgeLabel.implicitHeight + 4
            radius: height / 2
            color: Qt.rgba(Kirigami.Theme.highlightColor.r,
                           Kirigami.Theme.highlightColor.g,
                           Kirigami.Theme.highlightColor.b, 0.12)

            QQC2.Label {
                id: phaseBadgeLabel
                anchors.centerIn: parent
                text: "Phase " + compactRoot.phaseNumber
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                font.weight: Font.DemiBold
                color: Kirigami.Theme.highlightColor
            }
        }
    }
}
