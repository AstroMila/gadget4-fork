#!/usr/bin/env python3
"""
Visualize galaxy collision from edge-on perspective
Shows thin stellar disks colliding horizontally
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
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

def create_animation(output_dir='../output', save_file='edge_on.mp4', fps=2):
    """Create edge-on animation (X-Z view)"""
    
    # Find all snapshot files
    snapshot_files = sorted(glob.glob(os.path.join(output_dir, 'snapshot_*.hdf5')))
    
    if not snapshot_files:
        print(f"No snapshots found in {output_dir}")
        return
    
    print(f"Found {len(snapshot_files)} snapshots")
    print("View: Edge-on (X-Z plane)")
    
    # Load all snapshots
    snapshots = []
    for sfile in snapshot_files:
        print(f"Loading {os.path.basename(sfile)}...")
        snapshots.append(load_snapshot(sfile))
    
    # Determine coordinate limits - using X and Z
    all_x = []
    all_z = []
    for snap in snapshots:
        if len(snap['newstars_pos']) > 0:
            all_x.extend(snap['newstars_pos'][:, 0])
            all_z.extend(snap['newstars_pos'][:, 2])
        all_x.extend(snap['disk_pos'][:, 0])
        all_z.extend(snap['disk_pos'][:, 2])
        all_x.extend(snap['bulge_pos'][:, 0])
        all_z.extend(snap['bulge_pos'][:, 2])
    
    xlim = [np.percentile(all_x, 1), np.percentile(all_x, 99)]
    zlim = [np.percentile(all_z, 1), np.percentile(all_z, 99)]
    
    # Add some padding
    x_range = xlim[1] - xlim[0]
    z_range = zlim[1] - zlim[0]
    xlim = [xlim[0] - 0.1*x_range, xlim[1] + 0.1*x_range]
    
    # Make Z range much larger to fill the frame better
    # Expand Z to about 1/3 of X range for better visibility
    z_max = (xlim[1] - xlim[0]) / 3.0
    zlim = [-z_max, z_max]
    
    print(f"Coordinate range: X={xlim}, Z={zlim}")
    
    # Calculate figure size to match data aspect ratio (equal scaling)
    x_range = xlim[1] - xlim[0]
    z_range = zlim[1] - zlim[0]
    aspect_ratio = x_range / z_range
    fig_height = 8
    fig_width = fig_height * aspect_ratio
    
    # Create figure with aspect ratio matching the data
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor='black')
    ax.set_facecolor('black')
    ax.set_xlim(xlim)
    ax.set_ylim(zlim)
    ax.set_aspect('equal')  # Keep equal scaling
    ax.axis('off')
    
    # Remove margins to eliminate black borders
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    # Initialize empty scatter plots - X-Z plane
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
    
    # View label
    view_text = ax.text(0.98, 0.98, 'Edge-on view (X-Z plane)', 
                       transform=ax.transAxes, color='yellow', fontsize=12,
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
        
        # Plot pre-existing stars (disk + bulge) in X-Z plane
        old_pos = np.vstack([snap['disk_pos'], snap['bulge_pos']])
        old_stars.set_offsets(old_pos[:, [0, 2]])  # X and Z coordinates
        
        # Plot newly formed stars in X-Z plane
        if len(snap['newstars_pos']) > 0:
            new_stars.set_offsets(snap['newstars_pos'][:, [0, 2]])
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

def create_static_frames(output_dir='../output', frames_dir='frames'):
    """Create static PNG images for each snapshot - edge-on view"""
    
    # Create frames directory
    os.makedirs(frames_dir, exist_ok=True)
    
    # Find all snapshot files
    snapshot_files = sorted(glob.glob(os.path.join(output_dir, 'snapshot_*.hdf5')))
    
    print(f"Creating {len(snapshot_files)} static frames (edge-on view)...")
    
    # Load all snapshots
    snapshots = [load_snapshot(f) for f in snapshot_files]
    
    # Determine limits
    all_x = []
    all_z = []
    for snap in snapshots:
        if len(snap['newstars_pos']) > 0:
            all_x.extend(snap['newstars_pos'][:, 0])
            all_z.extend(snap['newstars_pos'][:, 2])
        all_x.extend(snap['disk_pos'][:, 0])
        all_z.extend(snap['disk_pos'][:, 2])
        all_x.extend(snap['bulge_pos'][:, 0])
        all_z.extend(snap['bulge_pos'][:, 2])
    
    xlim = [np.percentile(all_x, 1), np.percentile(all_x, 99)]
    zlim = [np.percentile(all_z, 1), np.percentile(all_z, 99)]
    x_range = xlim[1] - xlim[0]
    xlim = [xlim[0] - 0.1*x_range, xlim[1] + 0.1*x_range]
    
    # Make Z range much larger to fill the frame better
    z_max = (xlim[1] - xlim[0]) / 3.0
    zlim = [-z_max, z_max]
    
    # Calculate figure size to match data aspect ratio
    x_range = xlim[1] - xlim[0]
    z_range = zlim[1] - zlim[0]
    aspect_ratio = x_range / z_range
    fig_height = 8
    fig_width = fig_height * aspect_ratio
    
    for i, (sfile, snap) in enumerate(zip(snapshot_files, snapshots)):
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor='black')
        ax.set_facecolor('black')
        ax.set_xlim(xlim)
        ax.set_ylim(zlim)
        ax.set_aspect('equal')  # Keep equal scaling
        ax.axis('off')
        
        # Remove margins to eliminate black borders
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
        # Plot pre-existing stars - X-Z plane
        old_pos = np.vstack([snap['disk_pos'], snap['bulge_pos']])
        ax.scatter(old_pos[:, 0], old_pos[:, 2], c='white', s=0.2, alpha=0.4)
        
        # Plot newly formed stars - X-Z plane
        if len(snap['newstars_pos']) > 0:
            ax.scatter(snap['newstars_pos'][:, 0], snap['newstars_pos'][:, 2],
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
        
        ax.text(0.98, 0.98, 'Edge-on view (X-Z plane)',
               transform=ax.transAxes, color='yellow', fontsize=12,
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
    print("Galaxy Collision - Edge-On View (Stars Only)")
    print("=" * 60)
    
    # Check if output directory exists
    if not os.path.exists('../output'):
        print("Error: ../output/ directory not found")
        sys.exit(1)
    
    # Create static frames
    create_static_frames()
    
    print("\n" + "=" * 60)
    
    # Try to create animation
    try:
        create_animation()
    except Exception as e:
        print(f"Animation creation failed: {e}")
        print("Static frames were created successfully in frames/ directory")
