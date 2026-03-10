import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DashboardLoginCard from "../src/components/DashboardLoginCard.vue";

describe("DashboardLoginCard", () => {
  it("submits the password without requiring a username", async () => {
    const wrapper = mount(DashboardLoginCard, {
      props: {
        busy: false,
        errorMessage: "",
      },
    });

    await wrapper.get('input[type="password"]').setValue("panel-secret");
    await wrapper.get("form").trigger("submit.prevent");

    expect(wrapper.emitted("login")).toBeTruthy();
    expect(wrapper.emitted("login")?.[0]).toEqual(["panel-secret"]);
    expect(wrapper.text()).not.toContain("username");
  });
});
