import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../common" as Common

ColumnLayout {
    id: defaultRoot

    property string inputData: ""
    property string resultData: ""
    property bool isError: false

    spacing: Kirigami.Units.smallSpacing

    // Copy button row
    RowLayout {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignRight

        Common.CopyButton {
            textToCopy: defaultRoot.resultData
        }
    }

    // Input section
    QQC2.Label {
        text: "Input"
        font.weight: Font.Bold
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        opacity: 0.7
        visible: defaultRoot.inputData !== ""
    }

    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.maximumHeight: 200
        visible: defaultRoot.inputData !== ""

        QQC2.TextArea {
            text: defaultRoot.inputData
            readOnly: true
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            wrapMode: Text.Wrap

            background: Rectangle {
                color: Qt.rgba(0, 0, 0, 0.04)
                radius: Kirigami.Units.cornerRadius
            }
        }
    }

    // Result section
    QQC2.Label {
        text: defaultRoot.isError ? "Error" : "Result"
        font.weight: Font.Bold
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        opacity: 0.7
        color: defaultRoot.isError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
        visible: defaultRoot.resultData !== ""
    }

    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.maximumHeight: 300
        visible: defaultRoot.resultData !== ""

        QQC2.TextArea {
            text: defaultRoot.resultData
            readOnly: true
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            wrapMode: Text.Wrap
            color: defaultRoot.isError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor

            background: Rectangle {
                color: defaultRoot.isError
                    ? Qt.rgba(Kirigami.Theme.negativeTextColor.r,
                             Kirigami.Theme.negativeTextColor.g,
                             Kirigami.Theme.negativeTextColor.b, 0.05)
                    : Qt.rgba(0, 0, 0, 0.04)
                radius: Kirigami.Units.cornerRadius
            }
        }
    }
}
