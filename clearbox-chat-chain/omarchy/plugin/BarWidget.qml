import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "lamercey.clearbox-chat-chain"

  property bool online: false
  property int conversationCount: 0
  readonly property string baseUrl: String(setting("baseUrl", "http://127.0.0.1:3219")).replace(/\/$/, "")
  readonly property int refreshSeconds: Math.max(5, parseInt(setting("refreshIntervalSec", 15), 10) || 15)

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function notify() {
    var title = root.online ? "Clearbox Chat-Chain online" : "Clearbox Chat-Chain offline"
    var body = root.online ? (root.conversationCount + " durable conversation" + (root.conversationCount === 1 ? "" : "s")) : root.baseUrl
    Quickshell.execDetached(["omarchy-notification-send", title, body])
  }

  visible: true
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  IpcHandler {
    target: "lamercey.clearbox-chat-chain"
    function refresh(): void { root.refresh() }
    function status(): void { root.notify() }
  }

  Process {
    id: statusProc
    command: ["curl", "-fsS", "--max-time", "2", root.baseUrl + "/api/v1/conversations"]
    stdout: StdioCollector {
      id: statusOut
      waitForEnd: true
      onStreamFinished: {
        try {
          var rows = JSON.parse(text)
          root.conversationCount = Array.isArray(rows) ? rows.length : 0
          root.online = true
        } catch (e) {
          root.online = false
          root.conversationCount = 0
        }
      }
    }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.online = false
        root.conversationCount = 0
      }
    }
  }

  Process {
    id: createProc
    command: ["curl", "-fsS", "--max-time", "3", "-X", "POST", "-H", "Content-Type: application/json", "-d", "{\"title\":\"Omarchy conversation\"}", root.baseUrl + "/api/v1/conversations"]
    onExited: function(exitCode) {
      if (exitCode === 0) root.refresh()
      else root.notify()
    }
  }

  Timer {
    interval: root.refreshSeconds * 1000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.online ? "" : ""
    slotSize: Style.bar.statusSlot
    fontSize: Style.font.caption
    tooltipText: root.online ? ("Clearbox · " + root.conversationCount + " conversations") : "Clearbox API offline"
    onPressed: function(b) {
      if (b === Qt.RightButton && root.online && !createProc.running) createProc.running = true
      else if (b === Qt.MiddleButton) root.refresh()
      else root.notify()
    }
  }
}

