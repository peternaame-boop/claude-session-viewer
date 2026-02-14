import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "components/chat" as Chat

QQC2.ScrollView {
    id: chatRoot

    property bool autoScroll: true

    function scrollToIndex(idx) {
        chatRoot.autoScroll = false;
        chatList.positionViewAtIndex(idx, ListView.Center);
    }

    ListView {
        id: chatList
        model: ConversationModel
        clip: true
        spacing: Kirigami.Units.smallSpacing
        cacheBuffer: 600

        topMargin: Kirigami.Units.gridUnit
        bottomMargin: Kirigami.Units.gridUnit
        leftMargin: Kirigami.Units.gridUnit
        rightMargin: Kirigami.Units.gridUnit

        // "Load earlier" header when pagination is active
        header: Item {
            width: chatList.width - chatList.leftMargin - chatList.rightMargin
            height: ConversationModel.canLoadEarlier ? loadEarlierBtn.height + Kirigami.Units.largeSpacing : 0
            visible: ConversationModel.canLoadEarlier

            QQC2.Button {
                id: loadEarlierBtn
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: Kirigami.Units.smallSpacing
                text: "Load earlier messages (" + chatList.count + " of " + ConversationModel.totalChunkCount + " shown)"
                icon.name: "arrow-up"
                flat: true
                onClicked: ConversationModel.load_earlier()
            }
        }

        delegate: Loader {
            id: chunkLoader
            width: chatList.width - chatList.leftMargin - chatList.rightMargin

            required property int index
            required property string chunkId
            required property string chunkType
            required property string userText
            required property string aiText
            required property string systemText
            required property string status
            required property int toolCount
            required property var toolExecutions
            required property int tokenCount
            required property int duration
            required property real cost
            required property string modelName
            required property string timestamp
            required property int tokensFreed
            required property var commands
            required property var fileRefs
            required property var contextStats
            required property var processes
            required property int phaseNumber

            sourceComponent: {
                switch (chunkType) {
                    case "user": return userGroupComponent;
                    case "ai": return aiGroupComponent;
                    case "system": return systemGroupComponent;
                    case "compact": return compactGroupComponent;
                    default: return null;
                }
            }

            Component {
                id: userGroupComponent
                Chat.UserGroup {
                    userText: chunkLoader.userText
                    timestamp: chunkLoader.timestamp
                    commands: chunkLoader.commands
                    fileRefs: chunkLoader.fileRefs
                    width: chunkLoader.width
                }
            }

            Component {
                id: aiGroupComponent
                Chat.AIGroup {
                    modelName: chunkLoader.modelName
                    status: chunkLoader.status
                    toolCount: chunkLoader.toolCount
                    tokenCount: chunkLoader.tokenCount
                    duration: chunkLoader.duration
                    cost: chunkLoader.cost
                    aiText: chunkLoader.aiText
                    toolExecutions: chunkLoader.toolExecutions
                    contextStats: chunkLoader.contextStats
                    processes: chunkLoader.processes
                    width: chunkLoader.width
                }
            }

            Component {
                id: systemGroupComponent
                Chat.SystemGroup {
                    systemText: chunkLoader.systemText
                    timestamp: chunkLoader.timestamp
                    width: chunkLoader.width
                }
            }

            Component {
                id: compactGroupComponent
                Chat.CompactGroup {
                    tokensFreed: chunkLoader.tokensFreed
                    phaseNumber: chunkLoader.phaseNumber
                    width: chunkLoader.width
                }
            }
        }

        // Auto-scroll to bottom when new content arrives (if already at bottom)
        onCountChanged: {
            if (chatRoot.autoScroll) {
                Qt.callLater(positionViewAtEnd);
            }
        }

        onContentYChanged: {
            // Track whether user has scrolled away from bottom
            chatRoot.autoScroll = atYEnd;
        }

        // Empty state
        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: chatList.count === 0
            text: "No messages in this session"
            icon.name: "dialog-messages"
        }
    }
}
