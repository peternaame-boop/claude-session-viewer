import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

QQC2.Popup {
    id: palette

    // Center horizontally, offset from top
    parent: QQC2.Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round(parent.height * 0.15)
    width: Math.min(600, parent.width - Kirigami.Units.gridUnit * 4)
    height: Math.min(implicitHeight, 400)

    modal: true
    focus: true
    closePolicy: QQC2.Popup.CloseOnEscape | QQC2.Popup.CloseOnPressOutside

    padding: Kirigami.Units.smallSpacing

    onOpened: {
        searchField.text = "";
        searchField.forceActiveFocus();
        SearchResultModel.clear();
    }

    // Debounce timer for search
    Timer {
        id: debounceTimer
        interval: 200
        onTriggered: {
            if (searchField.text.length > 0) {
                SearchEngine.search(searchField.text, SessionManager.currentProjectId);
            } else {
                SearchResultModel.clear();
            }
        }
    }

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing

        // Search field
        QQC2.TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: SessionManager.currentProjectId !== ""
                ? "Search sessions..."
                : "Search projects..."
            focus: true

            onTextChanged: debounceTimer.restart()

            Keys.onUpPressed: {
                if (resultsList.count > 0) {
                    resultsList.currentIndex = Math.max(0, resultsList.currentIndex - 1);
                }
            }
            Keys.onDownPressed: {
                if (resultsList.count > 0) {
                    resultsList.currentIndex = Math.min(resultsList.count - 1, resultsList.currentIndex + 1);
                }
            }
            Keys.onReturnPressed: {
                if (resultsList.currentIndex >= 0 && resultsList.count > 0) {
                    resultsList.currentItem.activate();
                }
            }
        }

        // Results list
        QQC2.ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: Math.min(resultsList.contentHeight, 320)
            visible: resultsList.count > 0

            ListView {
                id: resultsList
                model: SearchResultModel
                clip: true
                currentIndex: 0
                keyNavigationEnabled: false

                delegate: QQC2.ItemDelegate {
                    id: resultDelegate
                    width: resultsList.width
                    highlighted: resultsList.currentIndex === index

                    required property int index
                    required property string sessionId
                    required property string projectId
                    required property string sessionTitle
                    required property string matchedText
                    required property string context
                    required property string messageType
                    required property real timestamp
                    required property int messageIndex

                    function activate() {
                        if (sessionId !== "") {
                            // Navigate to session and scroll to message
                            if (SessionManager.currentProjectId !== projectId) {
                                SessionManager.select_project(projectId);
                            }
                            SessionManager.select_session(sessionId);
                        } else if (projectId !== "") {
                            // Navigate to project
                            SessionManager.select_project(projectId);
                        }
                        palette.close();
                    }

                    contentItem: ColumnLayout {
                        spacing: 2

                        // Session title
                        QQC2.Label {
                            text: resultDelegate.sessionTitle
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            font.weight: Font.Bold
                        }

                        // Context with match highlighted
                        QQC2.Label {
                            text: resultDelegate.context
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            opacity: 0.8
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                        }

                        // Metadata row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            QQC2.Label {
                                text: resultDelegate.messageType
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                opacity: 0.5
                            }

                            QQC2.Label {
                                text: "·"
                                opacity: 0.3
                                visible: resultDelegate.timestamp > 0
                            }

                            QQC2.Label {
                                text: resultDelegate.timestamp > 0
                                    ? new Date(resultDelegate.timestamp * 1000).toLocaleDateString()
                                    : ""
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                opacity: 0.5
                                visible: resultDelegate.timestamp > 0
                            }
                        }
                    }

                    onClicked: activate()
                }
            }
        }

        // Empty state
        Kirigami.PlaceholderMessage {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            visible: resultsList.count === 0 && searchField.text.length > 0
            text: "No results found"
            icon.name: "search"
        }
    }
}
