#!/usr/bin/env python3
"""
Visualize galaxy collision from a tilted 3D perspective
Shows disk structure by rotating the view angle
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import h5py
import glob
import os

def rotate_3d(pos, angle_x=30, angle_z=20):
    """
    Rotate 3D coordinates to get a tilted view
    angle_x: rotation around X axis (tilt up/down) in degrees
    angle_z: rotation around Z axis (rotate left/right) in degrees
    """
    # Convert to radians
    ax = np.radians(angle_x)
    az = np.radians(angle_z)
    
    # Rotation matrix around X axis
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(ax), -np.sin(ax)],
        [0, np.sin(ax), np.cos(ax)]
    ])
    
    # Rotation matrix around Z axis
    Rz = np.array([
        [np.cos(az), -np.sin(az), 0],
        [np.sin(az), np.cos(az), 0],
        [0, 0, 1]
    ])
    
    # Apply rotations
    rotated = pos @ Rx.T @ Rz.T
    
    return rotated

def load_snapshot(filename):
    """Load particle data from HDF5 snapshot"""
    with h5py.File(filename, 'r') as f:
        # Get header info
        time = f['Header'].attrs['Time']
        
        data = {}
        
        # Load newly formed stars (PartType4)
        if 'PartType4' in f:
            data['newstars_pos'] = f['PartType4/Coordinates'][:]
            data['newstars_mass'] = f['PartType4/Masses'][:]
            data['newstars_time'] = f['PartType4/StellarFormationTime'][:]
        else:
            data['newstars_pos'] = np.array([]).reshape(0, 3)
            data['newstars_mass'] = np.array([])
            data['newstars_time'] = np.array([])
        
        # Load pre-existing stellar disk (PartType2)
        if 'PartType2' in f:
            data['disk_pos'] = f['PartType2/Coordinates'][:]
        else:
            data['disk_pos'] = np.array([]).reshape(0, 3)
        
        # Load bulge stars (PartType3)
        if 'PartType3' in f:
            data['bulge_pos'] = f['PartType3/Coordinates'][:]
        else:
            data['bulge_pos'] = np.array([]).reshape(0, 3)
        
        data['time'] = time
        
    return data

def create_animation(output_dir='../output', save_file='tilted_view.mp4', fps=2, 
                    angle_x=30, angle_z=20):
    """Create animation from tilted perspective"""
    
    # Find all snapshot files
    snapshot_files = sorted(glob.glob(os.path.join(output_dir, 'snapshot_*.hdf5')))
    
    if not snapshot_files:
        print(f"No snapshots found in {output_dir}")
        return
    
    print(f"Found {len(snapshot_files)} snapshots")
    print(f"Viewing angle: {angle_x}° tilt, {angle_z}° rotation")
    
    # Load all snapshots
    snapshots = []
    for sfile in snapshot_files:
        print(f"Loading {os.path.basename(sfile)}...")
        snapshots.append(load_snapshot(sfile))
    
    # Determine coordinate limits from rotated positions
    all_x = []
    all_y = []
    for snap in snapshots:
        # Combine all particle types and rotate
        all_pos = np.vstack([snap['disk_pos'], snap['bulge_pos']])
        if len(snap['newstars_pos']) > 0:
            all_pos = np.vstack([all_pos, snap['newstars_pos']])
        
        rotated = rotate_3d(all_pos, angle_x, angle_z)
        all_x.extend(rotated[:, 0])
        all_y.extend(rotated[:, 1])
    
    xlim = [np.percentile(all_x, 1), np.percentile(all_x, 99)]
    ylim = [np.percentile(all_y, 1), np.percentile(all_y, 99)]
    
    # Add some padding
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    xlim = [xlim[0] - 0.1*x_range, xlim[1] + 0.1*x_range]
    ylim = [ylim[0] - 0.1*y_range, ylim[1] + 0.1*y_range]
    
    print(f"Rotated coordinate range: X={xlim}, Y={ylim}")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10), facecolor='black')
    ax.set_facecolor('black')
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Initialize empty scatter plots
    old_stars = ax.scatter([], [], c='white', s=0.2, alpha=0.4, label='Pre-existing stars')
    new_stars = ax.scatter([], [], c='cyan', s=1.5, alpha=0.9, edgecolors='white', linewidths=0.1)
    
    # Time text
    time_text = ax.text(0.02, 0.98, '', transform=ax.transAxes, 
                       color='white', fontsize=14, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    
    # Star count text
    count_text = ax.text(0.02, 0.92, '', transform=ax.transAxes,
                        color='cyan', fontsize=12, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    
    # View angle text
    view_text = ax.text(0.98, 0.98, f'View: {angle_x}° tilt, {angle_z}° rotation', 
                       transform=ax.transAxes, color='yellow', fontsize=10,
                       verticalalignment='top', horizontalalignment='right',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    
    def init():
        old_stars.set_offsets(np.empty((0, 2)))
        new_stars.set_offsets(np.empty((0, 2)))
        time_text.set_text('')
        count_text.set_text('')
        return old_stars, new_stars, time_text, count_text, view_text
    
    def animate(frame):
        snap = snapshots[frame]
        
        # Rotate pre-existing stars (disk + bulge)
        old_pos = np.vstack([snap['disk_pos'], snap['bulge_pos']])
        old_rotated = rotate_3d(old_pos, angle_x, angle_z)
        old_stars.set_offsets(old_rotated[:, :2])
        
        # Rotate newly formed stars
        if len(snap['newstars_pos']) > 0:
            new_rotated = rotate_3d(snap['newstars_pos'], angle_x, angle_z)
            new_stars.set_offsets(new_rotated[:, :2])
        else:
            new_stars.set_offsets(np.empty((0, 2)))
        
        # Update text
        time_text.set_text(f"Time: {snap['time']:.3f} Gyr")
        count_text.set_text(f"New stars: {len(snap['newstars_pos']):,}")
        
        return old_stars, new_stars, time_text, count_text, view_text
    
    # Create animation
    print(f"\nCreating animation with {len(snapshots)} frames...")
    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                 frames=len(snapshots), interval=1000/fps,
                                 blit=True, repeat=True)
    
    # Save animation
    print(f"Saving animation to {save_file}...")
    try:
        anim.save(save_file, writer='ffmpeg', fps=fps, dpi=150,
                 extra_args=['-vcodec', 'libx264'])
        print(f"Animation saved successfully to {save_file}")
    except Exception as e:
        print(f"Could not save MP4 (ffmpeg might not be installed): {e}")
        print("Trying GIF format instead...")
        gif_file = save_file.replace('.mp4', '.gif')
        anim.save(gif_file, writer='pillow', fps=fps)
        print(f"Animation saved as GIF: {gif_file}")
    
    plt.close()
    
    print("\nDone!")

def create_static_frames(output_dir='../output', frames_dir='frames', 
                        angle_x=30, angle_z=20):
    """Create static PNG images for each snapshot from tilted view"""
    
    # Create frames directory
    os.makedirs(frames_dir, exist_ok=True)
    
    # Find all snapshot files
    snapshot_files = sorted(glob.glob(os.path.join(output_dir, 'snapshot_*.hdf5')))
    
    print(f"Creating {len(snapshot_files)} static frames from tilted view...")
    print(f"Viewing angle: {angle_x}° tilt, {angle_z}° rotation")
    
    # Load all snapshots
    snapshots = [load_snapshot(f) for f in snapshot_files]
    
    # Determine limits
    all_x = []
    all_y = []
    for snap in snapshots:
        all_pos = np.vstack([snap['disk_pos'], snap['bulge_pos']])
        if len(snap['newstars_pos']) > 0:
            all_pos = np.vstack([all_pos, snap['newstars_pos']])
        rotated = rotate_3d(all_pos, angle_x, angle_z)
        all_x.extend(rotated[:, 0])
        all_y.extend(rotated[:, 1])
    
    xlim = [np.percentile(all_x, 1), np.percentile(all_x, 99)]
    ylim = [np.percentile(all_y, 1), np.percentile(all_y, 99)]
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    xlim = [xlim[0] - 0.1*x_range, xlim[1] + 0.1*x_range]
    ylim = [ylim[0] - 0.1*y_range, ylim[1] + 0.1*y_range]
    
    for i, (sfile, snap) in enumerate(zip(snapshot_files, snapshots)):
        fig, ax = plt.subplots(figsize=(12, 10), facecolor='black')
        ax.set_facecolor('black')
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Plot pre-existing stars (rotated)
        old_pos = np.vstack([snap['disk_pos'], snap['bulge_pos']])
        old_rotated = rotate_3d(old_pos, angle_x, angle_z)
        ax.scatter(old_rotated[:, 0], old_rotated[:, 1], c='white', s=0.2, alpha=0.4)
        
        # Plot newly formed stars (rotated)
        if len(snap['newstars_pos']) > 0:
            new_rotated = rotate_3d(snap['newstars_pos'], angle_x, angle_z)
            ax.scatter(new_rotated[:, 0], new_rotated[:, 1],
                      c='cyan', s=1.5, alpha=0.9, edgecolors='white', linewidths=0.1)
        
        # Add text
        ax.text(0.02, 0.98, f"Time: {snap['time']:.3f} Gyr",
               transform=ax.transAxes, color='white', fontsize=14,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
        
        ax.text(0.02, 0.92, f"New stars: {len(snap['newstars_pos']):,}",
               transform=ax.transAxes, color='cyan', fontsize=12,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
        
        ax.text(0.98, 0.98, f'View: {angle_x}° tilt, {angle_z}° rotation',
               transform=ax.transAxes, color='yellow', fontsize=10,
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
        
        # Save frame
        frame_file = os.path.join(frames_dir, f'frame_{i:03d}.png')
        plt.savefig(frame_file, dpi=150, facecolor='black')
        plt.close()
        
        print(f"  Saved {frame_file}")
    
    print(f"\nAll frames saved to {frames_dir}/")

if __name__ == '__main__':
    import sys
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("=" * 60)
    print("Galaxy Collision - Tilted 3D View")
    print("=" * 60)
    
    # Check if output directory exists
    if not os.path.exists('../output'):
        print("Error: ../output/ directory not found")
        sys.exit(1)
    
    # Set viewing angles (adjust these to change perspective)
    angle_x = 30  # Tilt angle (degrees) - how much to tilt up
    angle_z = 20  # Rotation angle (degrees) - how much to rotate sideways
    
    # Create static frames
    create_static_frames(angle_x=angle_x, angle_z=angle_z)
    
    print("\n" + "=" * 60)
    
    # Try to create animation
    try:
        create_animation(angle_x=angle_x, angle_z=angle_z)
    except Exception as e:
        print(f"Animation creation failed: {e}")
        print("Static frames were created successfully in frames/ directory")
