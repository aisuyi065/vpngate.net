import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DashboardPasswordCard from "../src/components/DashboardPasswordCard.vue";

describe("DashboardPasswordCard", () => {
  it("emits the next password when submitted", async () => {
    const wrapper = mount(DashboardPasswordCard, {
      props: {
        busy: false,
        errorMessage: "",
      },
    });

    await wrapper.get('input[type="password"]').setValue("new-panel-secret");
    await wrapper.get("form").trigger("submit.prevent");

    expect(wrapper.emitted("changePassword")).toBeTruthy();
    expect(wrapper.emitted("changePassword")?.[0]).toEqual(["new-panel-secret"]);
  });
});
