import * as THREE from 'three';
import GUI from 'lil-gui';
import { Tree as EzTree } from '@dgreenheck/ez-tree';

type EzTreeOptions = EzTree['options'];

interface SceneManagerDebugAPI {
  getEzTreeOptions: () => EzTreeOptions | null;
  setEzTreeOptions: (opts: EzTreeOptions) => void;
  loadEzTreePreset: (name: string) => void;
  setMainLightPos: (x: number, y: number, z: number) => void;
  setLeafTexture: (index: number) => void;
  switchTheme: (style: string) => void;
}

const THEME_STYLES = ['default', 'sakura', 'cyberpunk', 'ink'] as const;

export class DebugGUI {
  private gui: GUI;
  private sm: SceneManagerDebugAPI;
  private presetObj = { preset: 'Oak Medium' };
  private lightObj = { azimuth: 45, elevation: 45 };
  private texObj = { texture: 0 };
  private themeObj = { style: 'default' };

  constructor(sceneManager: SceneManagerDebugAPI) {
    this.sm = sceneManager;
    this.gui = new GUI({ title: 'Tree Debug' });

    this.buildTreeFolder();
    this.buildLeafFolder();
    this.buildLightFolder();
    this.buildThemeFolder();
  }

  private buildTreeFolder() {
    const f = this.gui.addFolder('树形参数');
    const presets = [
      'Ash Small', 'Ash Medium', 'Ash Large',
      'Aspen Small', 'Aspen Medium', 'Aspen Large',
      'Oak Small', 'Oak Medium', 'Oak Large',
      'Pine Small', 'Pine Medium', 'Pine Large',
      'Bush 1', 'Bush 2', 'Bush 3',
    ];
    f.add(this.presetObj, 'preset', presets).name('预设').onChange(() => {
      this.sm.loadEzTreePreset(this.presetObj.preset);
    });
  }

  private buildLeafFolder() {
    const f = this.gui.addFolder('树叶');
    f.add(this.texObj, 'texture', { 'Leaves 1': 0, 'Leaves 2': 1, 'Leaves 3': 2 }).name('纹理').onChange((v: number) => {
      this.sm.setLeafTexture(v);
    });
  }

  private buildLightFolder() {
    const f = this.gui.addFolder('光照');
    f.add(this.lightObj, 'azimuth', 0, 360, 1).name('方位角').onChange(() => this.updateLightPos());
    f.add(this.lightObj, 'elevation', 0, 90, 1).name('仰角').onChange(() => this.updateLightPos());
  }

  private buildThemeFolder() {
    const f = this.gui.addFolder('风格');
    const options: Record<string, string> = {};
    for (const s of THEME_STYLES) options[s] = s;
    f.add(this.themeObj, 'style', options).name('主题').onChange((v: string) => {
      this.sm.switchTheme(v);
    });
  }

  private updateLightPos() {
    const az = THREE.MathUtils.degToRad(this.lightObj.azimuth);
    const el = THREE.MathUtils.degToRad(this.lightObj.elevation);
    const dist = 12;
    const x = Math.cos(el) * Math.cos(az) * dist;
    const y = Math.sin(el) * dist;
    const z = Math.cos(el) * Math.sin(az) * dist;
    this.sm.setMainLightPos(x, y, z);
  }

  dispose() {
    this.gui.destroy();
  }
}
