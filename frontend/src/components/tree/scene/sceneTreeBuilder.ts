import * as THREE from 'three'
import { Tree as EzTree } from '@dgreenheck/ez-tree'
import { deepMergeOptions } from './UserDataMapper'
import type { SceneState } from './sceneState'
import type { CameraRig } from './sceneCamera'
import type { TreeMaterials } from './sceneMaterials'
import type { OutlineBuilder } from './sceneOutlines'

export class TreeBuilder {
  private state: SceneState
  private cameraRig: CameraRig
  private materials: TreeMaterials
  private outlines: OutlineBuilder

  constructor(state: SceneState, cameraRig: CameraRig, materials: TreeMaterials, outlines: OutlineBuilder) {
    this.state = state
    this.cameraRig = cameraRig
    this.materials = materials
    this.outlines = outlines
  }

  applyOverrides(overrides: Record<string, any>) {
    if (!this.state.ezTree) return
    // Re-hydrate options from the base preset so stale sim keys don't linger
    this.state.ezTree.loadPreset('Oak Medium')
    // Deep-merge our overrides (adds new level keys that preset lacks)
    deepMergeOptions(this.state.ezTree.options, overrides)
    this.state.ezTree.generate()
    this.rebuildTreeGroups()
  }

  buildTreeMeshes() {
    this.state.ezTree = new EzTree()
    this.state.ezTree.loadPreset('Oak Medium')

    // Apply saved user overrides (deep-merge adds new level keys that
    // ez-tree's built-in copy() would skip)
    if (this.state.lastUserOverrides) {
      deepMergeOptions(this.state.ezTree.options, this.state.lastUserOverrides)
      this.state.ezTree.generate()
    }

    // Move branch and leaf meshes from ez-tree into our groups
    this.state.trunkGroup!.add(this.state.ezTree.branchesMesh)
    this.state.leavesGroup!.add(this.state.ezTree.leavesMesh)

    // Apply custom materials
    this.materials.applyCustomMaterials()

    // Update bounds for camera
    this.state.treeGroup!.updateMatrixWorld(true)
    this.state.treeBounds = new THREE.Box3().setFromObject(this.state.treeGroup!)
    this.state.treeCenter = new THREE.Vector3()
    this.state.treeBounds.getCenter(this.state.treeCenter)
    const size = new THREE.Vector3()
    this.state.treeBounds.getSize(size)

    // Build outline meshes (inverted-hull, default hidden)
    this.outlines.build()

    // Reposition camera if it already exists
    if (this.state.camera) {
      this.cameraRig.refit()
      // this.updateGroundLineY()
      // this.updateParticleSpawnArea()
    }
  }

  rebuildTreeGroups() {
    // Remove old meshes from groups (they belong to ez-tree)
    const trunkChildren = [...this.state.trunkGroup!.children]
    for (const child of trunkChildren) {
      this.state.trunkGroup!.remove(child)
    }
    const leafChildren = [...this.state.leavesGroup!.children]
    for (const child of leafChildren) {
      this.state.leavesGroup!.remove(child)
    }

    // Re-add ez-tree meshes
    if (this.state.ezTree) {
      this.state.trunkGroup!.add(this.state.ezTree.branchesMesh)
      this.state.leavesGroup!.add(this.state.ezTree.leavesMesh)
      // Re-apply custom materials (ez-tree generate() resets them)
      this.materials.applyCustomMaterials()
    }

    // Rebuild outline meshes with new geometry
    this.outlines.build()

    // Compute bounds
    this.state.treeGroup!.updateMatrixWorld(true)
    this.state.treeBounds = new THREE.Box3().setFromObject(this.state.treeGroup!)
    this.state.treeBounds.getCenter(this.state.treeCenter)
    const size = new THREE.Vector3()
    this.state.treeBounds.getSize(size)

    if (this.state.camera) {
      this.cameraRig.refit()
    }
  }
}
