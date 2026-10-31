from acteo.sequence_loader import group_by_fixed_size, group_by_timestamp_gap


def test_group_by_timestamp_gap_empty() -> None:
    assert group_by_timestamp_gap([]) == []


def test_group_by_fixed_size_groups_in_fixed_sizes() -> None:
    files = [f"/tmp/img{i}.jpg" for i in range(1, 8)]
    seqs = group_by_fixed_size(files, group_size=3)

    assert len(seqs) == 3
    assert [len(seq.image_paths) for seq in seqs] == [3, 3, 1]
    assert seqs[0].image_paths == files[:3]
    assert seqs[1].image_paths == files[3:6]
    assert seqs[2].image_paths == files[6:]
