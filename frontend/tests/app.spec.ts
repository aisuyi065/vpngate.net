import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import App from "../src/App.vue";

describe("App", () => {
  it("renders supported connection methods, IP quality, and connect action", async () => {
    const wrapper = mount(App);
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain("Supported Methods");
    expect(wrapper.text()).toContain("IP Quality");
    expect(wrapper.text()).toContain("Connect");
    expect(wrapper.findAll("tbody tr").length).toBeGreaterThan(0);
  });
});
