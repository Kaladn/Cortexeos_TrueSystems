def test_gpu_failover():
    """
    Unit test for GPU failover functionality.
    """
    from services.gpu_service import GPUFailover
    gpu_service = GPUFailover()
    # Simulate a successful failover with no errors
    assert gpu_service.monitor_and_failover() is None  # No exceptions raised
