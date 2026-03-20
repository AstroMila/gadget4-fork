#!/usr/bin/env python3
"""
Galaxy evolution time-series analysis for CollidingGalaxiesSFR simulation.

Produces 5 plots, each with left/right panels (one per galaxy):
  01_gas_mass.png             — Gas mass vs time
  02_stellar_mass.png         — Total stellar mass vs time
  03_sfr.png                  — Star formation rate vs time
  04_central_gas_density.png  — Gas density within 5 kpc of galaxy center vs time
  05_central_stellar_density.png — Stellar density within 5 kpc of galaxy center vs time

Also prints all available HDF5 fields from the snapshots (for reference).

Galaxy separation:
  Galaxies are identified from the initial snapshot (snapshot_000):
    Galaxy 1 = particles starting at X < 0  (center ~(-78, -23, 0) kpc)
    Galaxy 2 = particles starting at X > 0  (center ~(+77, +23, 0) kpc)
  Galaxy centers at later times are tracked using the bulge particles (PartType3),
  which are the most compact component and preserve structure through the collision.
  Newly formed stars (PartType4) have no initial position record, so they are
  assigned to whichever galaxy center they are closest to at each snapshot.

Units:
  Mass:    10^10 M_sun  (GADGET code unit: UnitMass = 1.989e43 g)
  Length:  kpc          (GADGET code unit: UnitLength = 3.085678e21 cm)
  Time:    Gyr          (written directly by GADGET into snapshot Header/Time)
  SFR:     M_sun / yr   (GADGET writes StarFormationRate in this unit)
  Density: 10^10 M_sun / kpc^3

Run from CollidingGalaxiesSFR/ directory:
    python -u analysis/plots/galaxy_evolution.py
"""

import os
import sys
import glob

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import h5py


# ── Configuration ──────────────────────────────────────────────────────────────

SNAPSHOT_DIR   = '../output'        # relative to analysis/  →  CollidingGalaxiesSFR/output
RESULTS_DIR    = 'results/plots'    # relative to analysis/  →  analysis/results/plots

CENTRAL_RADIUS = 5.0                              # kpc sphere for central density
SPHERE_VOLUME  = (4.0 / 3.0) * np.pi * CENTRAL_RADIUS ** 3   # kpc^3

# Plot colours
COLOR_GAL1 = '#4C9BE8'   # blue  – Galaxy 1
COLOR_GAL2 = '#E8784C'   # orange – Galaxy 2


# ── Data loading ───────────────────────────────────────────────────────────────

def build_galaxy_id_maps(snap0_file):
    """
    Read the initial snapshot and record which particle IDs belong to which galaxy.

    Galaxy 1 = initially at X < 0
    Galaxy 2 = initially at X > 0

    Only the collisionless / conserved particle types are tracked by ID:
      PartType0 (gas), PartType2 (disk stars), PartType3 (bulge stars).
    Newly formed stars (PartType4) are absent at t=0 and are handled separately.

    Returns
    -------
    dict  {ptype_str: (gal1_ids_array, gal2_ids_array)}
    """
    print("Building galaxy ID maps from snapshot_000 ...")
    maps = {}
    with h5py.File(snap0_file, 'r') as f:
        for ptype in ('PartType0', 'PartType2', 'PartType3'):
            if ptype not in f:
                continue
            coords = f[f'{ptype}/Coordinates'][:]
            ids    = f[f'{ptype}/ParticleIDs'][:]
            gal1_ids = ids[coords[:, 0] < 0]
            gal2_ids = ids[coords[:, 0] > 0]
            maps[ptype] = (gal1_ids, gal2_ids)
            print(f"  {ptype}: galaxy 1 = {len(gal1_ids):,}, "
                  f"galaxy 2 = {len(gal2_ids):,} particles")
    return maps


def get_galaxy_centers(f, bulge_gal1_ids, bulge_gal2_ids):
    """
    Compute center-of-mass positions for each galaxy using bulge (PartType3).

    Returns
    -------
    (center1, center2) — each a (3,) array in kpc
    """
    if 'PartType3' not in f:
        return np.zeros(3), np.zeros(3)

    coords = f['PartType3/Coordinates'][:]
    ids    = f['PartType3/ParticleIDs'][:]
    mask1  = np.isin(ids, bulge_gal1_ids)
    mask2  = np.isin(ids, bulge_gal2_ids)
    c1 = coords[mask1].mean(axis=0) if mask1.any() else np.zeros(3)
    c2 = coords[mask2].mean(axis=0) if mask2.any() else np.zeros(3)
    return c1, c2


def process_snapshot(filepath, id_maps, mass_table):
    """
    Load one snapshot and compute all evolution quantities for each galaxy.

    Parameters
    ----------
    filepath   : str         – path to HDF5 snapshot
    id_maps    : dict        – output of build_galaxy_id_maps()
    mass_table : array (6,)  – GADGET MassTable from Header (code units)

    Returns
    -------
    dict with keys 'time', 'gal1', 'gal2'.
    Each galaxy sub-dict contains:
      gas_mass, star_mass, sfr, cgas_dens, cstar_dens
    """
    bulge_ids = id_maps.get('PartType3', (np.array([]), np.array([])))

    with h5py.File(filepath, 'r') as f:
        time = float(f['Header'].attrs['Time'])
        c1, c2 = get_galaxy_centers(f, bulge_ids[0], bulge_ids[1])
        centers = [c1, c2]

        # per-galaxy accumulators: [galaxy1, galaxy2]
        gas_mass   = [0.0, 0.0]
        sfr_total  = [0.0, 0.0]
        cgas_mass  = [0.0, 0.0]
        star_mass  = [0.0, 0.0]
        cstar_mass = [0.0, 0.0]

        # ── Gas (PartType0) ────────────────────────────────────────────────────
        if 'PartType0' in f:
            g_ids    = f['PartType0/ParticleIDs'][:]
            g_coords = f['PartType0/Coordinates'][:]
            g_masses = f['PartType0/Masses'][:]
            g_sfr    = f['PartType0/StarFormationRate'][:]

            for gi, gal_id_arr in enumerate(id_maps.get('PartType0', (None, None))):
                if gal_id_arr is None:
                    continue
                mask = np.isin(g_ids, gal_id_arr)
                gas_mass[gi]  = float(g_masses[mask].sum())
                sfr_total[gi] = float(g_sfr[mask].sum())
                dist = np.linalg.norm(g_coords[mask] - centers[gi], axis=1)
                cgas_mass[gi] = float(g_masses[mask][dist < CENTRAL_RADIUS].sum())

        # ── Pre-existing stars: disk (PartType2) and bulge (PartType3) ─────────
        for ptype, mp in (('PartType2', mass_table[2]),
                          ('PartType3', mass_table[3])):
            if ptype not in f or ptype not in id_maps:
                continue
            s_ids    = f[f'{ptype}/ParticleIDs'][:]
            s_coords = f[f'{ptype}/Coordinates'][:]
            for gi, gal_id_arr in enumerate(id_maps[ptype]):
                mask   = np.isin(s_ids, gal_id_arr)
                n_part = int(mask.sum())
                star_mass[gi] += n_part * float(mp)
                dist = np.linalg.norm(s_coords[mask] - centers[gi], axis=1)
                cstar_mass[gi] += (dist < CENTRAL_RADIUS).sum() * float(mp)

        # ── Newly formed stars (PartType4) – assign by nearest galaxy center ───
        if 'PartType4' in f:
            n4_coords = f['PartType4/Coordinates'][:]
            n4_masses = f['PartType4/Masses'][:]
            dist1 = np.linalg.norm(n4_coords - c1, axis=1)
            dist2 = np.linalg.norm(n4_coords - c2, axis=1)

            for gi, n4_mask in enumerate([dist1 <= dist2, dist2 < dist1]):
                n4m = n4_masses[n4_mask]
                n4c = n4_coords[n4_mask]
                star_mass[gi] += float(n4m.sum())
                dist_cen = np.linalg.norm(n4c - centers[gi], axis=1)
                cstar_mass[gi] += float(n4m[dist_cen < CENTRAL_RADIUS].sum())

    return {
        'time': time,
        'gal1': {
            'gas_mass':   gas_mass[0],
            'star_mass':  star_mass[0],
            'sfr':        sfr_total[0],
            'cgas_dens':  cgas_mass[0]  / SPHERE_VOLUME,
            'cstar_dens': cstar_mass[0] / SPHERE_VOLUME,
        },
        'gal2': {
            'gas_mass':   gas_mass[1],
            'star_mass':  star_mass[1],
            'sfr':        sfr_total[1],
            'cgas_dens':  cgas_mass[1]  / SPHERE_VOLUME,
            'cstar_dens': cstar_mass[1] / SPHERE_VOLUME,
        },
    }


# ── Plotting ───────────────────────────────────────────────────────────────────

def make_two_panel_plot(times, g1_vals, g2_vals, ylabel, title, filename):
    """
    Save a two-panel figure: left = Galaxy 1, right = Galaxy 2.
    Both panels share the same Y axis.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    fig.suptitle(title, fontsize=14, fontweight='bold')

    for ax, vals, label, color in (
        (ax1, g1_vals, 'Galaxy 1  (initially X < 0)', COLOR_GAL1),
        (ax2, g2_vals, 'Galaxy 2  (initially X > 0)', COLOR_GAL2),
    ):
        ax.plot(times, vals, color=color, lw=2)
        ax.set_xlabel('Time (Gyr)', fontsize=12)
        ax.set_title(label, fontsize=11, color=color)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(times[0], times[-1])

    ax1.set_ylabel(ylabel, fontsize=12)
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")


# ── Snapshot field inventory ───────────────────────────────────────────────────

def print_available_fields(snapshot_files):
    """
    Print all HDF5 fields from both the first and a late snapshot, so fields
    that only appear after star formation begins (e.g. PartType4) are included.
    """
    ptype_names = {
        'PartType0': 'Gas',
        'PartType1': 'Dark Matter (collisionless)',
        'PartType2': 'Disk Stars (pre-existing)',
        'PartType3': 'Bulge Stars (pre-existing)',
        'PartType4': 'Newly Formed Stars',
    }

    print("\n" + "=" * 65)
    print("AVAILABLE SNAPSHOT FIELDS")
    print("=" * 65)

    # Use last snapshot so PartType4 is fully populated
    check_file = snapshot_files[-1]
    print(f"(from {os.path.basename(check_file)})\n")

    with h5py.File(check_file, 'r') as f:
        print("Header attributes:")
        for k, v in f['Header'].attrs.items():
            print(f"  {k:35s}: {v}")
        print()

        for ptype, name in ptype_names.items():
            if ptype not in f:
                continue
            npart = f[ptype][list(f[ptype].keys())[0]].shape[0]
            print(f"{ptype}  —  {name}  ({npart:,} particles):")
            for field in sorted(f[ptype].keys()):
                ds = f[ptype][field]
                print(f"  {field:35s}: shape={ds.shape}, dtype={ds.dtype}")
            print()

    print("=" * 65 + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # Run from analysis/ directory so paths are consistent with other scripts
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    analysis_dir = os.path.dirname(script_dir)   # …/CollidingGalaxiesSFR/analysis/
    os.chdir(analysis_dir)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Find snapshots
    snapshot_files = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, 'snapshot_*.hdf5')))
    if not snapshot_files:
        print(f"Error: No snapshots found in {SNAPSHOT_DIR}")
        sys.exit(1)
    print(f"Found {len(snapshot_files)} snapshots in {SNAPSHOT_DIR}")

    # Print available fields (covers boss's last question)
    print_available_fields(snapshot_files)

    # Galaxy ID maps from t=0
    id_maps = build_galaxy_id_maps(snapshot_files[0])

    # Mass table (for disk and bulge particles whose masses are not stored per-particle)
    with h5py.File(snapshot_files[0], 'r') as f:
        mass_table = f['Header'].attrs['MassTable']
    print(f"\nMassTable (10^10 M_sun): {mass_table}")
    print(f"  PartType2 (disk)  mass per particle: {mass_table[2]:.5e} × 10^10 M_sun"
          f" = {mass_table[2]*1e10:.0f} M_sun")
    print(f"  PartType3 (bulge) mass per particle: {mass_table[3]:.5e} × 10^10 M_sun"
          f" = {mass_table[3]*1e10:.0f} M_sun")
    print()

    # Process all snapshots
    print("Processing snapshots ...")
    results = []
    for i, snap_file in enumerate(snapshot_files):
        print(f"  [{i+1:3d}/{len(snapshot_files)}] {os.path.basename(snap_file)}")
        results.append(process_snapshot(snap_file, id_maps, mass_table))

    times = np.array([r['time'] for r in results])

    def ts(key, gal):
        return np.array([r[gal][key] for r in results])

    # ── 1. Gas mass ─────────────────────────────────────────────────────────────
    print("\nGenerating plots ...")
    make_two_panel_plot(
        times,
        ts('gas_mass', 'gal1'), ts('gas_mass', 'gal2'),
        ylabel=r'Gas Mass  ($10^{10}\,M_\odot$)',
        title='Gas Mass vs Time',
        filename=os.path.join(RESULTS_DIR, '01_gas_mass.png'),
    )

    # ── 2. Stellar mass ─────────────────────────────────────────────────────────
    make_two_panel_plot(
        times,
        ts('star_mass', 'gal1'), ts('star_mass', 'gal2'),
        ylabel=r'Stellar Mass  ($10^{10}\,M_\odot$)',
        title='Stellar Mass vs Time\n(disk + bulge + newly formed stars)',
        filename=os.path.join(RESULTS_DIR, '02_stellar_mass.png'),
    )

    # ── 3. Star formation rate ──────────────────────────────────────────────────
    make_two_panel_plot(
        times,
        ts('sfr', 'gal1'), ts('sfr', 'gal2'),
        ylabel=r'SFR  ($M_\odot\,\mathrm{yr}^{-1}$)',
        title='Star Formation Rate vs Time',
        filename=os.path.join(RESULTS_DIR, '03_sfr.png'),
    )

    # ── 4. Central gas density ──────────────────────────────────────────────────
    make_two_panel_plot(
        times,
        ts('cgas_dens', 'gal1'), ts('cgas_dens', 'gal2'),
        ylabel=fr'Central Gas Density  ($10^{{10}}\,M_\odot\,\mathrm{{kpc}}^{{-3}}$)',
        title=f'Central Gas Density vs Time  (within {CENTRAL_RADIUS:.0f} kpc of galaxy center)',
        filename=os.path.join(RESULTS_DIR, '04_central_gas_density.png'),
    )

    # ── 5. Central stellar density ──────────────────────────────────────────────
    make_two_panel_plot(
        times,
        ts('cstar_dens', 'gal1'), ts('cstar_dens', 'gal2'),
        ylabel=fr'Central Stellar Density  ($10^{{10}}\,M_\odot\,\mathrm{{kpc}}^{{-3}}$)',
        title=f'Central Stellar Density vs Time  (within {CENTRAL_RADIUS:.0f} kpc of galaxy center)',
        filename=os.path.join(RESULTS_DIR, '05_central_stellar_density.png'),
    )

    print(f"\nAll plots saved to analysis/{RESULTS_DIR}/")
    print("Done!")


if __name__ == '__main__':
    main()
