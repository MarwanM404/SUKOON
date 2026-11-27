import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const PILL_CLASS = {
    upcoming: "text-bg-info",
    in_stay: "text-bg-warning",
    completed: "text-bg-success",
    cancelled: "text-bg-danger",
    pending: "text-bg-warning",
    in_progress: "text-bg-info",
    done: "text-bg-success",
};

export class SukoonDashboard extends Component {
    static template = "sukoon_pms.Dashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call("sukoon.reservation", "get_dashboard_data", []);
    }

    pillClass(state) {
        return PILL_CLASS[state] || "text-bg-secondary";
    }

    openList(resModel, name, domain, viewTypes = ["list", "form"]) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: resModel,
            views: viewTypes.map((v) => [false, v]),
            domain: domain || [],
            target: "current",
        });
    }

    openRecord(resModel, resId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: resId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    newRecord(resModel) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openArrivals() {
        this.openList("sukoon.reservation", _t("Arriving in 7 days"), this.state.data.domains.arrivals);
    }
    openDepartures() {
        this.openList("sukoon.reservation", _t("Departing in 7 days"), this.state.data.domains.departures);
    }
    openOpenTasks() {
        this.openList("sukoon.task", _t("Open tasks"), this.state.data.domains.open_tasks, ["list", "kanban", "form"]);
    }
    openMonth() {
        this.openList("sukoon.reservation", _t("This month's bookings"), this.state.data.domains.month);
    }
    openProperties() {
        this.action.doAction("sukoon_pms.action_sukoon_property");
    }
}

registry.category("actions").add("sukoon_pms.dashboard", SukoonDashboard);
