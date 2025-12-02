Your goal is to create a new home assistant integration that mimics the existing Lovelace frontend component.

The component's repo is available at https://github.com/modrzew/lovelace-temperature-map/, it's also available at /Users/modrzew/Projects/lovelace-temperature-map directory.

Its purpose is to get a list of temperature sensors and then paint a map of the apartment with a heatmap of interpolated temperatures.

The problem we're trying to solve is that doing all of this in the frontend takes a lot of time. Instead I want this to be a home assistant integration that redraws the map in the background once every 15 minutes and exposes an image entity that can be rendered.

We will probably also need some frontend component to make it possible to render the sensor dots and make them clickable.

Make sure the heatmap algorithm is properly ported from the original repo. We basically want exactly the same thing but as an integration that exposes an entity.

## Resources

Home assistant example components: https://github.com/home-assistant/example-custom-config/tree/master/custom_components/

Home assistant custom integration docs: https://developers.home-assistant.io/docs/creating_component_index

## Other remarks

Be lightweight on tests, focus on testing the core functionality.

When preparing the plan please don't split it into "phases" or "sprints". Just a list of tasks.
