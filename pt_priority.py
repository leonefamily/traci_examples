#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 18:53:29 2026

@author: leonefamily
"""
import os
import sys
import argparse
from pathlib import Path
from typing import Union, List, Optional, Any, Dict
from collections import defaultdict

if 'SUMO_HOME' in os.environ:
    sys.path.append(
        os.path.join(
            os.environ['SUMO_HOME'],
            'tools'
        )
    )
    import traci  # noqa
else:
    raise ImportError(
        'Failed to load traci module, because environment variable '
        'SUMO_HOME cannot be found. This might happed if SUMO '
        'installation is not system-wide or is misconfigured'
    )


def get_green_phase_id(
        tls_programs: dict,
        tls_id: str,
        maneuver_num: int
) -> int:
    """
    Get ID of a phase where requested maneuver has green light.

    Only works for TLS with a single logic.

    Parameters
    ----------
    tls_programs : dict
        TLS programs as a dictionary.
    tls_id : str
        ID of TLS that should be searched.
    maneuver_num : int
        Maneuver ID within ``tls_id``.

    Returns
    -------
    int

    """
    for idx, phase_info in enumerate(tls_programs[tls_id][0].phases):
        if phase_info.state[maneuver_num] in ['g', 'G']:
            return idx
    raise ValueError(
        'Requested maneuver ID does not have a phase where it has green'
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse configuration arguments for running TraCI"
    )

    parser.add_argument(
        '--sumo-config-path',
        required=True,
        help="Path to the SUMO configuration file"
    )
    parser.add_argument(
        '--prefer-lines',
        type=str,
        help="List of lines to prefer (comma-separated)",
        required=True,
        default=None
    )
    parser.add_argument(
        '--tls-ids',
        help="List of TLS IDs to use (comma-separated). Optional",
        default=None
    )
    parser.add_argument(
        '--flatpak',
        action='store_true',
        default=False,
        help="Launch TraCI using Flatpak-specific command nn Linux"
    )
    parser.add_argument(
        '--until',
        type=int,
        default=3600,
        help="Duration of simulation in seconds"
    )
    parser.add_argument(
        '--tls-distance',
        type=float,
        default=50.0,
        help="Distance threshold for TLS to activate priority"
    )
    parser.add_argument(
        '--request-blocking-duration',
        type=int,
        default=10,
        help=(
            "Duration in seconds during which new requests at the same "
            "TLS are not accepted when the other one is active"
        )
    )

    args = parser.parse_args()

    prefer_lines_list = [
        line.strip() for line in args.prefer_lines.split(',') if line.strip()
    ]
    args.prefer_lines = prefer_lines_list
    if not prefer_lines_list:
         raise RuntimeError(
             "--prefer-lines provided but resulted in no valid lines."
         )

    if args.tls_ids:
        tls_ids_list = [
            tls.strip() for tls in args.tls_ids.split(',') if tls.strip()
        ]
        args.tls_ids = tls_ids_list
        if not tls_ids_list:
            raise RuntimeError(
                "--tls-ids provided but resulted in no valid IDs"
            )

    if args.until <= 0:
        raise RuntimeError("--until must be a positive integer.")

    if args.tls_distance <= 0:
        raise RuntimeError("--tls-distance must be a positive float")

    if args.request_blocking_duration <= 0:
        raise RuntimeError(
            "--request-blocking-duration must be a positive integer"
        )

    return args


def main(
        sumo_config_path: Union[Path, str],
        prefer_lines: List[str],
        tls_ids: Optional[List[str]] = None,
        flatpak: bool = False,
        until: int = 3600,
        tls_distance: float = 50,
        request_blocking_duration: int = 10
):
    # prikaz, kterym TraCI otevre SUMO, pripadne jeho graficke rozhrani
    if flatpak and sys.platform.lower() == 'linux':
        # pro Flatpak-verzi SUMO na Linuxu
        sumo_cmd = [
            "flatpak",
            "run",
            "org.eclipse.sumo",
            "-c",
            sumo_config_path,
        ]
    else:
        sumo_cmd = [
            "sumo-gui",
            "-c",
            sumo_config_path,  # cesta k SUMO-konfiguraci
        ]   

    # provedeme pripojeni k serveru
    traci.start(sumo_cmd)

    # prvni krok simulace
    step = 0

    # promenna pro ukladani ID pristiho pozadavku
    next_request_id = 0

    # ziskame vsechny programy SSZ (i kdyz je SSZ jen jedno)
    tls_programs = {
        tls_id: traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)
        for tls_id in traci.trafficlight.getIDList()
        if (True if not tls_ids else tls_id in tls_ids)
    }
    
    # definujeme prazdnou promennou pro ukladani pozadavku
    requests = defaultdict(list)
    
    # simulace pobezi, dokud nebude `until` sekund
    while step < until:
    
        # posuneme simulaci o krok dopredu (cili o simulacni sekundu)
        traci.simulationStep()
    
        # zjistime vsechna vozidla, o kterych simulace v danem okamziku vi
        vehicles_ids = traci.vehicle.getIDList()
    
        # prohledavame kazde ID vozidla
        for vehicle_id in vehicles_ids:
    
            # zjistime, zda vozidlo jede po preferovane lince
            if traci.vehicle.getLine(vehicle_id) in prefer_lines:
                # ziskame ID svetelne rizenych krizovatek po trase vozidla
                # prvni je nejblizsi
                upcoming_tls_ids = traci.vehicle.getNextTLS(vehicle_id)
    
                if upcoming_tls_ids:
                    
                    # ziskame informace o nejblizsich svetlech:
                    # jejich ID, cislo pohybu, ktery vozidlo planue vyuzit,
                    # vzdalenost k nemu a aktualni signal
                    tls_info = upcoming_tls_ids[0]                
                    tls_id, maneuver_num, tls_dist, tls_signal = tls_info
                    
                    # pripadne vynechame SSZ, ktere nemame zvolene
                    if tls_id not in tls_programs:
                        continue
    
                    # pokud je vzdalenost mensi nez `tls_distance` metru
                    if tls_dist < tls_distance:
    
                        if tls_signal in ['g', 'G', 'y', 'Y']:
                            # nedelame nic, pokud i tak sviti zelena nebo zluta
                            continue
    
                        # Poradi aktualni faze
                        current_phase = traci.trafficlight.getPhase(tls_id)
                        # ID faze, ktera ma pro dany pohyb zelenou
                        green_phase = get_green_phase_id(
                            tls_programs=tls_programs,
                            tls_id=tls_id,
                            maneuver_num=maneuver_num
                        )
    
                        # zajistime nemoznost prekryvani vice pozadavku
                        skip_request = False
                        for request in requests[tls_id]:
                            if request['start_time'] <= step <= request['expiry_time']:
                                skip_request = True
                                break
    
                        if skip_request:
                            continue
    
                        # ulozime informace o pozadavku
                        requests[tls_id].append({
                            'request_id': next_request_id, # ID pro jednoznacnou identifikaci pozadavku
                            'vehicle_id': vehicle_id, # ID pozadujiciho vozidla
                            'start_time': step - request_blocking_duration,  # kdy pozadavek vznikl + ochrana pred prehozenim
                            'expiry_time': step + 5 + request_blocking_duration,  # kdy ma byt pozadavek vymazan
                            'instructions': {
                                 # prepnuti stavajiciho pozadavku na zlutou
                                 step: current_phase + 1,
                                 # nabeh cervene se zlutou pro preferovany smer
                                 step + 3: green_phase - 1,
                                 # zelena pro preferovany smer
                                 step + 5: green_phase,
                             }
                        })
                        # navysime ID o 1 pro pripadny pristi pozadavek
                        next_request_id += 1
    
        remove_request_ids = []  # pro ukladani pripadnych ID k vymazani
    
        # zjistime, jake pozadavky aplikovat, a jake vymazat
        for tls_id, tls_requests in requests.items():
            for request in tls_requests:
                # pokud je pozadavek aktualni v danem case, podivame se, zda ho neaplikujeme
                if step >= request['start_time'] and step < request['expiry_time']:
                    for action_step, requested_phase in request['instructions'].items():
                        # pokud se shoduje cas
                        if step == action_step:
                            curr_tls_phases = tls_programs[tls_id][0].phases
                            # opravime hledany index faze pomoci modula, aby nepresahl delku seznamu
                            requested_phase_fix = requested_phase % len(curr_tls_phases)
                            # aplikujeme fazi
                            traci.trafficlight.setPhase(tls_id, requested_phase_fix)
                            # neni potreba delat nic dale, opustime cyklus
                            break
                # pokud pozadavek jiz vyprsel, zaradime do seznamu na smazani
                elif step >= request['expiry_time']:
                    remove_request_ids.append(
                        (tls_id, request['request_id'])
                    )
    
        # smazeme neaktualni pozadavky
        for rem_tls_id, rem_request_id in remove_request_ids:
            remove_num = None
            for request_num, request in enumerate(requests[rem_tls_id]):
                if request['request_id'] == rem_request_id:
                    remove_num = request_num
            if remove_num is not None:
                del requests[rem_tls_id][remove_num]
    
        # navysime krok simulace o 1
        step += 1
    
    # odpojime server TraCI od simulace
    traci.close()


if __name__ == '__main__':
    args = parse_arguments()
    main(
        sumo_config_path=args.sumo_config_path,
        prefer_lines=args.prefer_lines,
        tls_ids=args.tls_ids,
        flatpak=args.flatpak,
        until=args.until,
        tls_distance=args.tls_distance,
        request_blocking_duration=args.request_blocking_duration
    )
