const Applet = imports.ui.applet;
const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;
const PopupMenu = imports.ui.popupMenu;

const UPDATE_INTERVAL = 60;

function MyApplet(orientation, panel_height, instance_id) {
    this._init(orientation, panel_height, instance_id);
}

MyApplet.prototype = {
    __proto__: Applet.TextIconApplet.prototype,

    _init: function(orientation, panel_height, instance_id) {
        Applet.TextIconApplet.prototype._init.call(this, orientation, panel_height, instance_id);
        
        this.set_applet_icon_symbolic_name("input-mouse-symbolic");
        this.set_applet_label("--%");
        
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);

        this._deviceLabel = new PopupMenu.PopupMenuItem("Logitech G Pro X Superlight 2 SE", { reactive: false });
        this._deviceLabel.label.set_style("font-weight: bold; font-size: 1.1em;");
        this.menu.addMenuItem(this._deviceLabel);

        this._batteryLabel = new PopupMenu.PopupMenuItem("Battery: --%", { reactive: false });
        this.menu.addMenuItem(this._batteryLabel);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._refreshItem = new PopupMenu.PopupMenuItem("Refresh Now");
        this._refreshItem.connect('activate', () => this._updateBattery());
        this.menu.addMenuItem(this._refreshItem);

        this._updateBattery();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, UPDATE_INTERVAL, () => {
            this._updateBattery();
            return true;
        });
    },

    _findBatteryPath: function(filename) {
        let sysfs = Gio.file_new_for_path("/sys/class/power_supply/");
        let enumerator = sysfs.enumerate_children("standard::name", Gio.FileQueryInfoFlags.NONE, null);
        let info;
        while ((info = enumerator.next_file(null)) !== null) {
            let name = info.get_name();
            if (name.indexOf("hidpp_battery_") === 0) {
                return "/sys/class/power_supply/" + name + "/" + filename;
            }
        }
        return null;
    },

    _updateBattery: function() {
        try {
            let cap_path = this._findBatteryPath("capacity");
            let status_path = this._findBatteryPath("status");
            
            if (!cap_path || !status_path) {
                this._setDisconnectedState("Mouse not detected");
                return;
            }
            
            let status_file = Gio.file_new_for_path(status_path);
            let [sOk, sContents] = status_file.load_contents(null);
            let status = sContents.toString().trim();
            
            // If status is "Unknown", the mouse is turned off
            if (status === "Unknown" || status === "") {
                this._setDisconnectedState("Mouse turned off");
                return;
            }
            
            let file = Gio.file_new_for_path(cap_path);
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
