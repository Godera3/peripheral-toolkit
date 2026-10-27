const Applet = imports.ui.applet;
const GLib = imports.gi.GLib;
const Mainloop = imports.mainloop;
const PopupMenu = imports.ui.popupMenu;

function MyApplet(orientation, panel_height, instance_id) {
    this._init(orientation, panel_height, instance_id);
}

MyApplet.prototype = {
    __proto__: Applet.TextIconApplet.prototype,

    _init: function(orientation, panel_height, instance_id) {
        Applet.TextIconApplet.prototype._init.call(this, orientation, panel_height, instance_id);
        
        // Use the headset icon instead of a battery
        this.set_applet_icon_symbolic_name("audio-headset-symbolic");
        this.set_applet_label("--%");
        
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);

        this._deviceLabel = new PopupMenu.PopupMenuItem("Razer Barracuda X Chroma", { reactive: false });
        this._deviceLabel.label.set_style("font-weight: bold; font-size: 1.1em;");
        this.menu.addMenuItem(this._deviceLabel);

        this._batteryLabel = new PopupMenu.PopupMenuItem("Battery: --%", { reactive: false });
        this.menu.addMenuItem(this._batteryLabel);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._refreshItem = new PopupMenu.PopupMenuItem("Refresh Now");
        this._refreshItem.connect('activate', () => this._updateBattery());
        this.menu.addMenuItem(this._refreshItem);

        this._updateBattery();
    },

    _updateBattery: function() {
        try {
            let script_path = GLib.get_home_dir() + "/Desktop/peripheral-toolkit/headset/cli/barracuda.py";
            let [ok, stdout, stderr, status] = GLib.spawn_command_line_sync("/usr/bin/python3 " + script_path + " battery");
            
            if (ok && status === 0) {
                let out = String(stdout);
                let match = out.match(/Battery: (-?\d+)%/);
                if (match) {
                    let level = parseInt(match[1]);
                    
                    this.set_applet_label(level + "%");
                    this.set_applet_tooltip("Razer Barracuda X Chroma\nBattery: " + level + "%");
                    
                    // Keep headset icon, change text color based on level
                    this.set_applet_icon_symbolic_name("audio-headset-symbolic");
                    
                    if (level < 20) {
                        this._applet_label.set_style("color: #ff5555; font-weight: bold;"); // Red
                    } else if (level < 50) {
                        this._applet_label.set_style("color: #fce94f; font-weight: bold;"); // Yellow
                    } else {
                        this._applet_label.set_style("color: #8ae234;"); // Green
                    }

                    this._batteryLabel.label.set_text("Battery: " + level + "%");
                }
            } else {
                this.set_applet_label("--%");
                this.set_applet_tooltip("Razer Barracuda X Chroma\nDisconnected or asleep");
                this.set_applet_icon_symbolic_name("audio-headset-symbolic");
                this._applet_label.set_style("color: #888888;"); // Grey
                this._batteryLabel.label.set_text("Battery: Disconnected");
            }
        } catch(e) {
            global.logError("Razer Battery Applet: " + e);
        }
        
        if (this._timeout) Mainloop.source_remove(this._timeout);
        this._timeout = Mainloop.timeout_add_seconds(60, this._updateBattery.bind(this));
    },
    
    on_applet_clicked: function(event) {
        this.menu.toggle();
    },
    
    on_applet_removed_from_panel: function() {
        if (this._timeout) {
            Mainloop.source_remove(this._timeout);
        }
    }
};

function main(metadata, orientation, panel_height, instance_id) {
    return new MyApplet(orientation, panel_height, instance_id);
}
