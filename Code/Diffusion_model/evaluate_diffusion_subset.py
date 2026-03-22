import csv
import argparse
from pathlib import Path

import numpy as np
import torch
from skimage.metrics import structural_similarity

from guided_sampling_3var import guidance_3var


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "Copernicus_processed_data"
SAVE_DIR = SCRIPT_DIR / "Save"

CHECKPOINT = SCRIPT_DIR / "Save" / "lightning_logs" / "version_4" / "checkpoints" / "epoch=39-step=5920.ckpt"

TEST_FILES = {
    "sss": DATA_DIR / "so_test.npy",
    "sst": DATA_DIR / "thetao_test.npy",
    "ssh": DATA_DIR / "zos_test.npy",
}

TEST_INDICES = [0, 60, 120, 180, 240, 300]
R1, R2 = 30, 33
NUM_TIMESTEPS = 50
K_SAMPLES = 15
BASE_SEED = 526557

MODES = {
    "DIFF-SST-SSH": False,
    "DIFF-SST-SSH-GE": True,
}


def rmse(pred, true):
    return float(np.sqrt(np.mean((pred - true) ** 2)))


def ssim_score(pred, true):
    data_min = float(min(pred.min(), true.min()))
    data_max = float(max(pred.max(), true.max()))
    data_range = max(data_max - data_min, 1e-8)
    return float(structural_similarity(pred, true, data_range=data_range))


def select_medoid(samples):
    sample_stack = np.stack(samples, axis=0)
    mean_image = sample_stack.mean(axis=0)
    distances = np.sum((sample_stack - mean_image) ** 2, axis=(1, 2, 3))
    best_idx = int(np.argmin(distances))
    return sample_stack[best_idx], best_idx


def save_rows(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["mode", "index", "selected_sample_id", "rmse", "ssim"])
        writer.writeheader()
        writer.writerows(rows)


def evaluate_mode(mode_name, grad_enhancing, indices, k_samples):
    rows = []

    for index in indices:
        samples = []
        true_sss = None

        for sample_id in range(k_samples):
            seed = BASE_SEED + index * 100 + sample_id
            final_image, ref_sss, _, _, _, _ = guidance_3var(
                checkpoint=str(CHECKPOINT),
                fname_sss=str(TEST_FILES["sss"]),
                fname_sst=str(TEST_FILES["sst"]),
                fname_ssh=str(TEST_FILES["ssh"]),
                index=index,
                r1=R1,
                r2=R2,
                num_timesteps=NUM_TIMESTEPS,
                seed=seed,
                grad_enhancing=grad_enhancing,
                device=torch.device("cuda:0"),
            )
            samples.append(final_image)
            true_sss = ref_sss

        selected_sample, selected_idx = select_medoid(samples)
        pred_sss = selected_sample[0]
        rows.append(
            {
                "mode": mode_name,
                "index": index,
                "selected_sample_id": selected_idx,
                "rmse": rmse(pred_sss, true_sss),
                "ssim": ssim_score(pred_sss, true_sss),
            }
        )
        print(mode_name, "index", index, rows[-1])

    return rows


def main():
    parser = argparse.ArgumentParser(description="Subset evaluation for diffusion SSS test metrics.")
    parser.add_argument(
        "--indices",
        nargs="*",
        type=int,
        default=TEST_INDICES,
        help="Test indices to evaluate. Defaults to a six-date seasonal subset.",
    )
    parser.add_argument(
        "--k-samples",
        type=int,
        default=K_SAMPLES,
        help="Number of stochastic samples used before medoid selection.",
    )
    parser.add_argument(
        "--output",
        default=str(SAVE_DIR / "subset_test_metrics_epoch39.csv"),
        help="CSV file to save subset metrics.",
    )
    args = parser.parse_args()

    all_rows = []
    output_path = Path(args.output)

    for mode_name, grad_enhancing in MODES.items():
        mode_rows = evaluate_mode(mode_name, grad_enhancing, args.indices, args.k_samples)
        all_rows.extend(mode_rows)
        save_rows(all_rows, output_path)

        rmse_mean = float(np.mean([row["rmse"] for row in mode_rows]))
        ssim_mean = float(np.mean([row["ssim"] for row in mode_rows]))
        print(mode_name, {"mean_rmse": rmse_mean, "mean_ssim": ssim_mean})

    save_rows(all_rows, output_path)
    print(f"Saved subset evaluation to {output_path}")


if __name__ == "__main__":
    main()
