const Applet = imports.ui.applet;
const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;
const PopupMenu = imports.ui.popupMenu;

const BATTERY_PATH = "/sys/class/power_supply/hidpp_battery_0/capacity";
const UPDATE_INTERVAL = 60;

function MyApplet(orientation, panel_height, instance_id) {
    this._init(orientation, panel_height, instance_id);
}

MyApplet.prototype = {
    __proto__: Applet.TextIconApplet.prototype,

    _init: function(orientation, panel_height, instance_id) {
        Applet.TextIconApplet.prototype._init.call(this, orientation, panel_height, instance_id);
        
        // Use a mouse icon instead of a battery icon
        this.set_applet_icon_symbolic_name("input-mouse-symbolic");
        this.set_applet_label("--%");
        
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);

        // Menu Header
        this._deviceLabel = new PopupMenu.PopupMenuItem("Logitech G Pro X Superlight 2 SE", { reactive: false });
        this._deviceLabel.label.set_style("font-weight: bold; font-size: 1.1em;");
        this.menu.addMenuItem(this._deviceLabel);

        // Battery Text in Menu
        this._batteryLabel = new PopupMenu.PopupMenuItem("Battery: --%", { reactive: false });
        this.menu.addMenuItem(this._batteryLabel);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Refresh Button
        this._refreshItem = new PopupMenu.PopupMenuItem("Refresh Now");
        this._refreshItem.connect('activate', () => this._updateBattery());
        this.menu.addMenuItem(this._refreshItem);

        this._updateBattery();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, UPDATE_INTERVAL, () => {
            this._updateBattery();
            return true;
        });
    },

    _updateBattery: function() {
        try {
            let file = Gio.file_new_for_path(BATTERY_PATH);
            if (!file.query_exists(null)) {
                this._setDisconnectedState("Mouse not detected");
                return;
            }
            
            let [ok, contents] = file.load_contents(null);
            let level = parseInt(contents.toString().trim());
            
            if (isNaN(level)) {
                this._setDisconnectedState("Invalid data");
                return;
            }

            this.set_applet_label(level + "%");
            this.set_applet_tooltip("Logitech G Pro X Superlight 2 SE\nBattery: " + level + "%");
            this.set_applet_icon_symbolic_name("input-mouse-symbolic");
            this._batteryLabel.label.set_text("Battery: " + level + "%");

            if (level < 20) {
                this._applet_label.set_style("color: #ff5555; font-weight: bold;"); // Red
            } else if (level < 50) {
                this._applet_label.set_style("color: #fce94f; font-weight: bold;"); // Yellow
            } else {
                this._applet_label.set_style("color: #8ae234;"); // Green
            }

        } catch(e) {
            global.logError("Logitech Battery Applet: " + e);
            this._setDisconnectedState("Error reading battery");
        }
    },

    _setDisconnectedState: function(reason) {
        this.set_applet_label("--%");
        this.set_applet_tooltip("Logitech Mouse\n" + reason);
        this.set_applet_icon_symbolic_name("input-mouse-symbolic");
        this._applet_label.set_style("color: #888888;"); // Grey
        this._batteryLabel.label.set_text("Battery: " + reason);
    },
    
    on_applet_clicked: function(event) {
        this.menu.toggle();
    },
    
    on_applet_removed_from_panel: function() {
        if (this._timer) {
            GLib.source_remove(this._timer);
            this._timer = null;
        }
    }
};

function main(metadata, orientation, panel_height, instance_id) {
    return new MyApplet(orientation, panel_height, instance_id);
}
