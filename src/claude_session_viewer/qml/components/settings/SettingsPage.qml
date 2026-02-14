import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import com.claude.viewer 1.0

Kirigami.ScrollablePage {
    id: settingsPage
    title: "Settings"

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        // --- General ---
        Kirigami.FormLayout {
            Kirigami.Heading { text: "General"; level: 3 }

            QQC2.TextField {
                Kirigami.FormData.label: "Session directory:"
                text: ConfigManager.get_string("general/sessionDir")
                onEditingFinished: ConfigManager.set_string("general/sessionDir", text)
            }

            QQC2.SpinBox {
                Kirigami.FormData.label: "Max recent sessions:"
                value: ConfigManager.get_int("general/maxRecentSessions")
                from: 10
                to: 500
                onValueModified: ConfigManager.set_int("general/maxRecentSessions", value)
            }

            QQC2.Switch {
                Kirigami.FormData.label: "Show costs:"
                checked: ConfigManager.get_bool("general/showCosts")
                onToggled: ConfigManager.set_bool("general/showCosts", checked)
            }

            QQC2.Switch {
                Kirigami.FormData.label: "Auto-refresh on file change:"
                checked: ConfigManager.get_bool("general/autoRefresh")
                onToggled: ConfigManager.set_bool("general/autoRefresh", checked)
            }
        }

        Kirigami.Separator { Layout.fillWidth: true }

        // --- Appearance ---
        Kirigami.FormLayout {
            Kirigami.Heading { text: "Appearance"; level: 3 }

            QQC2.SpinBox {
                Kirigami.FormData.label: "Code font size:"
                value: ConfigManager.get_int("appearance/codeFontSize")
                from: 8
                to: 24
                onValueModified: ConfigManager.set_int("appearance/codeFontSize", value)
            }

            QQC2.Switch {
                Kirigami.FormData.label: "Word wrap:"
                checked: ConfigManager.get_bool("appearance/wordWrap")
                onToggled: ConfigManager.set_bool("appearance/wordWrap", checked)
            }

            QQC2.Switch {
                Kirigami.FormData.label: "Compact mode:"
                checked: ConfigManager.get_bool("appearance/compactMode")
                onToggled: ConfigManager.set_bool("appearance/compactMode", checked)
            }
        }

        Kirigami.Separator { Layout.fillWidth: true }

        // --- Notifications ---
        Kirigami.FormLayout {
            Kirigami.Heading { text: "Notifications"; level: 3 }

            QQC2.Switch {
                Kirigami.FormData.label: "Enabled:"
                checked: ConfigManager.get_bool("notifications/enabled")
                onToggled: ConfigManager.set_bool("notifications/enabled", checked)
            }

            QQC2.Switch {
                Kirigami.FormData.label: "Sound:"
                checked: ConfigManager.get_bool("notifications/sound")
                onToggled: ConfigManager.set_bool("notifications/sound", checked)
            }
        }

        Kirigami.Separator { Layout.fillWidth: true }

        // --- SSH ---
        Kirigami.FormLayout {
            Kirigami.Heading { text: "SSH"; level: 3 }

            QQC2.SpinBox {
                Kirigami.FormData.label: "Poll interval (ms):"
                value: ConfigManager.get_int("ssh/pollInterval")
                from: 1000
                to: 30000
                stepSize: 1000
                onValueModified: ConfigManager.set_int("ssh/pollInterval", value)
            }

            QQC2.SpinBox {
                Kirigami.FormData.label: "Connection timeout (s):"
                value: ConfigManager.get_int("ssh/timeout")
                from: 5
                to: 60
                onValueModified: ConfigManager.set_int("ssh/timeout", value)
            }

            // SSH profiles
            Kirigami.Heading { text: "Saved Profiles"; level: 4 }

            Repeater {
                model: ConfigManager.get_ssh_profiles()

                QQC2.ItemDelegate {
                    Layout.fillWidth: true
                    contentItem: RowLayout {
                        QQC2.Label { text: modelData.name; Layout.fillWidth: true }
                        QQC2.Label { text: modelData.host; opacity: 0.6 }
                        QQC2.ToolButton {
                            icon.name: "network-connect"
                            onClicked: SshManager.connect_ssh(
                                modelData.name, modelData.host,
                                modelData.port, modelData.username,
                                modelData.keyPath
                            )
                        }
                        QQC2.ToolButton {
                            icon.name: "edit-delete"
                            onClicked: ConfigManager.remove_ssh_profile(modelData.name)
                        }
                    }
                }
            }
        }

        Kirigami.Separator { Layout.fillWidth: true }

        // --- Advanced ---
        Kirigami.FormLayout {
            Kirigami.Heading { text: "Advanced"; level: 3 }

            QQC2.Switch {
                Kirigami.FormData.label: "Debug logging:"
                checked: ConfigManager.get_bool("advanced/debugLogging")
                onToggled: ConfigManager.set_bool("advanced/debugLogging", checked)
            }

            QQC2.Button {
                text: "Clear Cache"
                icon.name: "edit-clear-all"
                onClicked: {
                    ConfigManager.clear_cache();
                    cacheCleared.visible = true;
                }
            }

            QQC2.Label {
                id: cacheCleared
                text: "Cache cleared."
                visible: false
                color: Kirigami.Theme.positiveTextColor
            }
        }
    }
}
