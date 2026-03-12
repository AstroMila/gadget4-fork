#!/usr/bin/env python3
"""
Visualize galaxy collision simulation snapshots
Creates an animation showing newly formed stars over time
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle
import h5py
import glob
import os

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

def create_animation(output_dir='output', save_file='galaxy_collision.mp4', fps=2):
    """Create animation from all snapshots"""
    
    # Find all snapshot files
    snapshot_files = sorted(glob.glob(os.path.join(output_dir, 'snapshot_*.hdf5')))
    
    if not snapshot_files:
        print(f"No snapshots found in {output_dir}")
        return
    
    print(f"Found {len(snapshot_files)} snapshots")
    
    # Load all snapshots
    snapshots = []
    for sfile in snapshot_files:
        print(f"Loading {os.path.basename(sfile)}...")
        snapshots.append(load_snapshot(sfile))
    
    # Determine coordinate limits from all snapshots
    all_x = []
    all_y = []
    for snap in snapshots:
        if len(snap['newstars_pos']) > 0:
            all_x.extend(snap['newstars_pos'][:, 0])
            all_y.extend(snap['newstars_pos'][:, 1])
        all_x.extend(snap['disk_pos'][:, 0])
        all_y.extend(snap['disk_pos'][:, 1])
        all_x.extend(snap['bulge_pos'][:, 0])
        all_y.extend(snap['bulge_pos'][:, 1])
    
    xlim = [np.percentile(all_x, 1), np.percentile(all_x, 99)]
    ylim = [np.percentile(all_y, 1), np.percentile(all_y, 99)]
    
    # Add some padding
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    xlim = [xlim[0] - 0.1*x_range, xlim[1] + 0.1*x_range]
    ylim = [ylim[0] - 0.1*y_range, ylim[1] + 0.1*y_range]
    
    print(f"Coordinate range: X={xlim}, Y={ylim}")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10), facecolor='black')
    ax.set_facecolor('black')
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Initialize empty scatter plots
    old_stars = ax.scatter([], [], c='white', s=0.1, alpha=0.3, label='Pre-existing stars')
    new_stars = ax.scatter([], [], c='cyan', s=1.0, alpha=0.8, label='Newly formed stars')
    
    # Time text
    time_text = ax.text(0.02, 0.98, '', transform=ax.transAxes, 
                       color='white', fontsize=14, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    
    # Star count text
    count_text = ax.text(0.02, 0.92, '', transform=ax.transAxes,
                        color='cyan', fontsize=12, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    
    def init():
        old_stars.set_offsets(np.empty((0, 2)))
        new_stars.set_offsets(np.empty((0, 2)))
        time_text.set_text('')
        count_text.set_text('')
        return old_stars, new_stars, time_text, count_text
    
    def animate(frame):
        snap = snapshots[frame]
        
        # Plot pre-existing stars (disk + bulge)
        old_pos = np.vstack([snap['disk_pos'][:, :2], snap['bulge_pos'][:, :2]])
        old_stars.set_offsets(old_pos)
        
        # Plot newly formed stars
        if len(snap['newstars_pos']) > 0:
            new_stars.set_offsets(snap['newstars_pos'][:, :2])
        else:
            new_stars.set_offsets(np.empty((0, 2)))
        
        # Update text
        time_text.set_text(f"Time: {snap['time']:.3f} Gyr")
        count_text.set_text(f"New stars: {len(snap['newstars_pos']):,}")
        
        return old_stars, new_stars, time_text, count_text
    
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

def create_static_frames(output_dir='output', frames_dir='frames'):
    """Create static PNG images for each snapshot"""
    
    # Create frames directory
    os.makedirs(frames_dir, exist_ok=True)
    
    # Find all snapshot files
    snapshot_files = sorted(glob.glob(os.path.join(output_dir, 'snapshot_*.hdf5')))
    
    print(f"Creating {len(snapshot_files)} static frames...")
    
    # Load first and last to determine limits
    snapshots = [load_snapshot(f) for f in snapshot_files]
    
    all_x = []
    all_y = []
    for snap in snapshots:
        if len(snap['newstars_pos']) > 0:
            all_x.extend(snap['newstars_pos'][:, 0])
            all_y.extend(snap['newstars_pos'][:, 1])
        all_x.extend(snap['disk_pos'][:, 0])
        all_y.extend(snap['disk_pos'][:, 1])
        all_x.extend(snap['bulge_pos'][:, 0])
        all_y.extend(snap['bulge_pos'][:, 1])
    
    xlim = [np.percentile(all_x, 1), np.percentile(all_x, 99)]
    ylim = [np.percentile(all_y, 1), np.percentile(all_y, 99)]
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    xlim = [xlim[0] - 0.1*x_range, xlim[1] + 0.1*x_range]
    ylim = [ylim[0] - 0.1*y_range, ylim[1] + 0.1*y_range]
    
    for i, (sfile, snap) in enumerate(zip(snapshot_files, snapshots)):
        fig, ax = plt.subplots(figsize=(10, 10), facecolor='black')
        ax.set_facecolor('black')
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Plot pre-existing stars
        old_pos = np.vstack([snap['disk_pos'][:, :2], snap['bulge_pos'][:, :2]])
        ax.scatter(old_pos[:, 0], old_pos[:, 1], c='white', s=0.1, alpha=0.3)
        
        # Plot newly formed stars
        if len(snap['newstars_pos']) > 0:
            ax.scatter(snap['newstars_pos'][:, 0], snap['newstars_pos'][:, 1],
                      c='cyan', s=1.0, alpha=0.8)
        
        # Add text
        ax.text(0.02, 0.98, f"Time: {snap['time']:.3f} Gyr",
               transform=ax.transAxes, color='white', fontsize=14,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
        
        ax.text(0.02, 0.92, f"New stars: {len(snap['newstars_pos']):,}",
               transform=ax.transAxes, color='cyan', fontsize=12,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
        
        # Save frame
        frame_file = os.path.join(frames_dir, f'frame_{i:03d}.png')
        plt.savefig(frame_file, dpi=150, facecolor='black')
        plt.close()
        
        print(f"  Saved {frame_file}")
    
    print(f"\nAll frames saved to {frames_dir}/")
    print(f"You can create a video with: ffmpeg -framerate 2 -i {frames_dir}/frame_%03d.png -c:v libx264 -pix_fmt yuv420p galaxy_collision.mp4")

if __name__ == '__main__':
    import sys
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("=" * 60)
    print("Galaxy Collision Visualization")
    print("=" * 60)
    
    # Check if output directory exists
    if not os.path.exists('output'):
        print("Error: output/ directory not found")
        sys.exit(1)
    
    # Create static frames (always works)
    create_static_frames()
    
    print("\n" + "=" * 60)
    
    # Try to create animation
    try:
        create_animation()
    except Exception as e:
        print(f"Animation creation failed: {e}")
        print("Static frames were created successfully in frames/ directory")
