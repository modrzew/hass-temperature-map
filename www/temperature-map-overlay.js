/**
 * Temperature Map Overlay Card
 *
 * A custom Lovelace card that displays a temperature map image entity
 * with clickable sensor dots overlaid on top.
 *
 * Configuration (minimal - reads from entity attributes):
 * type: custom:temperature-map-overlay
 * image_entity: image.temperature_map_living_room
 *
 * Or with explicit configuration (overrides entity attributes):
 * type: custom:temperature-map-overlay
 * image_entity: image.temperature_map_living_room
 * sensors:
 *   - entity: sensor.living_room_temp
 *     x: 100
 *     y: 100
 *   - entity: sensor.bedroom_temp
 *     x: 200
 *     y: 150
 * rotation: 0  # Optional: 0, 90, 180, 270
 */

class TemperatureMapOverlay extends HTMLElement {
  setConfig(config) {
    if (!config.image_entity) {
      throw new Error('You must specify image_entity');
    }

    this._config = config;

    if (!this.content) {
      this.innerHTML = `
        <ha-card>
          <div class="card-content" style="position: relative; padding: 0;">
            <img
              id="heatmap-image"
              style="width: 100%; height: auto; display: block;"
            />
            <div
              id="sensor-overlay"
              style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
            ></div>
          </div>
        </ha-card>
      `;
      this.content = this.querySelector('.card-content');
      this.image = this.querySelector('#heatmap-image');
      this.overlay = this.querySelector('#sensor-overlay');
    }
  }

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;

    // Only re-render if relevant entities changed
    if (this._shouldUpdate(oldHass, hass)) {
      this._render();
    }
  }

  _shouldUpdate(oldHass, newHass) {
    if (!oldHass || !this._config) {
      return true;
    }

    // Check if image entity changed
    const oldImageEntity = oldHass.states[this._config.image_entity];
    const newImageEntity = newHass.states[this._config.image_entity];

    if (!oldImageEntity || !newImageEntity) {
      return true;
    }

    if (oldImageEntity.attributes.entity_picture !== newImageEntity.attributes.entity_picture) {
      return true;
    }

    // Check if any sensor entity changed (for overlay updates)
    const sensors = this._config.sensors || newImageEntity.attributes.sensors || [];
    for (const sensor of sensors) {
      const oldSensor = oldHass.states[sensor.entity];
      const newSensor = newHass.states[sensor.entity];
      if (!oldSensor || !newSensor || oldSensor.state !== newSensor.state) {
        return true;
      }
    }

    return false;
  }

  _render() {
    if (!this._hass || !this._config) {
      return;
    }

    // Get image entity
    const entity = this._hass.states[this._config.image_entity];
    if (!entity) {
      this.image.alt = 'Image entity not found';
      return;
    }

    // Get sensors and rotation from entity attributes or config
    // Config takes precedence for backwards compatibility
    const sensors = this._config.sensors || entity.attributes.sensors || [];
    const rotation = this._config.rotation !== undefined
      ? this._config.rotation
      : (entity.attributes.rotation || 0);

    // Set image URL using entity_picture (includes auth token)
    const imageUrl = entity.attributes.entity_picture;
    if (!imageUrl) {
      this.image.alt = 'Image not available';
      return;
    }

    // Only update image src if it changed to avoid unnecessary reloads
    if (this.image.src !== imageUrl) {
      this.image.src = imageUrl;
    }

    // If no sensors configured, just show the image without overlays
    if (!sensors || sensors.length === 0) {
      console.warn('No sensors configured for temperature map overlay - showing image only');
      return;
    }

    // Clear existing sensor overlays
    this.overlay.innerHTML = '';

    // Wait for image to load to get dimensions
    this.image.onload = () => {
      const imgRect = this.image.getBoundingClientRect();
      const imgNaturalWidth = this.image.naturalWidth;
      const imgNaturalHeight = this.image.naturalHeight;

      if (!imgNaturalWidth || !imgNaturalHeight) {
        return;
      }

      // Calculate scaling factor
      const scale = imgRect.width / imgNaturalWidth;

      // Render sensor dots
      sensors.forEach(sensor => {
        const sensorEntity = this._hass.states[sensor.entity];
        if (!sensorEntity) {
          return;
        }

        // Apply rotation to coordinates if needed
        let x = sensor.x;
        let y = sensor.y;
        let width = imgNaturalWidth;
        let height = imgNaturalHeight;

        if (rotation === 90) {
          [x, y] = [imgNaturalHeight - y, x];
          [width, height] = [height, width];
        } else if (rotation === 180) {
          [x, y] = [imgNaturalWidth - x, imgNaturalHeight - y];
        } else if (rotation === 270) {
          [x, y] = [y, imgNaturalWidth - x];
          [width, height] = [height, width];
        }

        // Scale coordinates to displayed image size
        const displayX = x * scale;
        const displayY = y * scale;

        // Create sensor dot
        const dot = document.createElement('div');
        dot.style.position = 'absolute';
        dot.style.left = `${displayX}px`;
        dot.style.top = `${displayY}px`;
        dot.style.width = '12px';
        dot.style.height = '12px';
        dot.style.borderRadius = '50%';
        dot.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
        dot.style.border = '2px solid #333';
        dot.style.transform = 'translate(-50%, -50%)';
        dot.style.cursor = 'pointer';
        dot.style.zIndex = '10';

        // Add click handler
        dot.addEventListener('click', () => this._handleSensorClick(sensor.entity));

        // Add hover effect
        dot.addEventListener('mouseenter', () => {
          dot.style.backgroundColor = 'rgba(255, 255, 255, 1)';
          dot.style.transform = 'translate(-50%, -50%) scale(1.2)';
        });
        dot.addEventListener('mouseleave', () => {
          dot.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
          dot.style.transform = 'translate(-50%, -50%)';
        });

        this.overlay.appendChild(dot);
      });
    };
  }

  _handleSensorClick(entityId) {
    const event = new CustomEvent('hass-more-info', {
      detail: { entityId },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  getCardSize() {
    return 3;
  }
}

customElements.define('temperature-map-overlay', TemperatureMapOverlay);

// Inform Home Assistant about the card
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'temperature-map-overlay',
  name: 'Temperature Map Overlay',
  description: 'Display temperature map with clickable sensor overlays',
});

console.info(
  '%c TEMPERATURE-MAP-OVERLAY %c 1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;',
);
